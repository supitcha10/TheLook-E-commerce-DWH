-- Default ATOMIC procedure. Install after 00/01/02. Call in autocommit mode.
-- expected_inputs and expected_money are session TEMP tables created by rendered run_batch.sql.
-- Only this procedure is the supported writer of stg/dw; do not call pieces independently.
CREATE OR REPLACE PROCEDURE etl.load_batch(
    p_batch_id VARCHAR(64), p_package_hash VARCHAR(64), p_observed_at TIMESTAMPTZ,
    p_iam_role VARCHAR(512), p_schema_version VARCHAR(32), p_rule_version VARCHAR(64))
AS $$
DECLARE
    r RECORD;
    v_n BIGINT;
    v_expected BIGINT;
    v_sum DECIMAL(38,6);
    v_old_hash VARCHAR(64);
    v_old_time TIMESTAMPTZ;
    v_bootstrap BOOLEAN;
    v_min_date DATE;
    v_max_date DATE;
    v_days INTEGER;
BEGIN
    -- Serialize every writer for this pipeline, including no-op/retry decisions.
    LOCK TABLE etl.batch_ledger;
    IF p_batch_id IS NULL OR LEN(p_batch_id)=0 OR p_observed_at IS NULL
       OR p_package_hash IS NULL OR LEN(p_package_hash)<>64
       OR p_iam_role IS NULL OR LEN(p_iam_role)=0
       OR p_schema_version IS NULL OR p_schema_version<>'dw-v1'
       OR p_rule_version IS NULL OR p_rule_version<>'provisional-v1' THEN
        RAISE EXCEPTION 'Invalid batch arguments or unsupported schema/rule version';
    END IF;
    IF EXISTS (SELECT batch_id FROM etl.batch_ledger GROUP BY batch_id HAVING COUNT(*)>1) THEN
        RAISE EXCEPTION 'Ledger contains duplicate batch IDs';
    END IF;
    SELECT COUNT(*) INTO v_n FROM etl.batch_ledger WHERE batch_id=p_batch_id;
    IF v_n=1 THEN
        SELECT package_hash, observed_at INTO v_old_hash, v_old_time FROM etl.batch_ledger WHERE batch_id=p_batch_id;
        IF v_old_hash<>p_package_hash OR v_old_time<>p_observed_at THEN
            RAISE EXCEPTION 'Existing batch ID has different inputs/configuration';
        END IF;
        INSERT INTO etl.batch_attempts VALUES(p_batch_id,GETDATE(),'NO_OP','Already published; no data or versions changed');
        RETURN;
    END IF;
    IF EXISTS (SELECT 1 FROM etl.batch_ledger WHERE observed_at>=p_observed_at) THEN
        RAISE EXCEPTION 'New observation time must be later than previous published batches';
    END IF;
    IF EXISTS (SELECT 1 FROM etl.batch_ledger WHERE rule_version<>p_rule_version OR schema_version<>p_schema_version) THEN
        RAISE EXCEPTION 'Rule/schema change requires a reviewed migration, not automatic SCD';
    END IF;
    SELECT COUNT(*)=0 INTO v_bootstrap FROM etl.batch_ledger;
    IF v_bootstrap AND (EXISTS(SELECT 1 FROM dw.dim_users) OR EXISTS(SELECT 1 FROM dw.dim_products)
                       OR EXISTS(SELECT 1 FROM dw.dim_distribution_centers) OR EXISTS(SELECT 1 FROM dw.fact_sales)) THEN
        RAISE EXCEPTION 'Bootstrap requires empty warehouse dimensions/facts';
    END IF;

    -- Validate temp input controls before interpolating any identifiers.
    SELECT COUNT(*) INTO v_n FROM expected_inputs;
    IF v_n<>7 OR EXISTS(SELECT table_name FROM expected_inputs GROUP BY table_name HAVING COUNT(*)<>1)
       OR EXISTS(SELECT 1 FROM expected_inputs WHERE table_name NOT IN
          ('distribution_centers','products','users','orders','order_items','inventory_items','events')
          OR expected_rows IS NULL OR expected_rows<=0 OR manifest_url IS NULL
          OR manifest_url NOT LIKE 's3://%' OR file_sha256 IS NULL OR LEN(file_sha256)<>64) THEN
        RAISE EXCEPTION 'Expected exactly seven nonempty, distinct approved input manifests';
    END IF;
    SELECT COUNT(*) INTO v_n FROM expected_money;
    IF v_n<>5 OR EXISTS(SELECT table_name,column_name FROM expected_money GROUP BY 1,2 HAVING COUNT(*)>1)
       OR EXISTS(SELECT 1 FROM expected_money WHERE expected_sum IS NULL OR NOT
          ((table_name='products' AND column_name IN ('cost','retail_price'))
           OR (table_name='inventory_items' AND column_name IN ('cost','product_retail_price'))
           OR (table_name='order_items' AND column_name='sale_price'))) THEN
        RAISE EXCEPTION 'Expected five monetary controls from validated curated report';
    END IF;
    FOR r IN SELECT * FROM expected_inputs ORDER BY table_name LOOP
        EXECUTE 'DELETE FROM stg.' || QUOTE_IDENT(r.table_name);
        EXECUTE 'COPY stg.' || QUOTE_IDENT(r.table_name) || ' FROM ' || QUOTE_LITERAL(r.manifest_url)
             || ' IAM_ROLE ' || QUOTE_LITERAL(p_iam_role) || ' MANIFEST FORMAT AS PARQUET';
    END LOOP;

    IF EXISTS (SELECT id FROM stg.distribution_centers GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'distribution_centers: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.distribution_centers;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='distribution_centers';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'distribution_centers: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.distribution_centers WHERE id<=0) THEN RAISE EXCEPTION 'distribution_centers.id: nonpositive key'; END IF;
    IF EXISTS (SELECT id FROM stg.products GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'products: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.products;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='products';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'products: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.products WHERE id<=0) THEN RAISE EXCEPTION 'products.id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.products WHERE distribution_center_id<=0) THEN RAISE EXCEPTION 'products.distribution_center_id: nonpositive key'; END IF;
    IF EXISTS (SELECT id FROM stg.users GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'users: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.users;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='users';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'users: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.users WHERE id<=0) THEN RAISE EXCEPTION 'users.id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.users WHERE city_missing_token <> (LOWER(TRIM(city))='null') OR (city_missing_token AND city_clean IS NOT NULL) OR (NOT city_missing_token AND (city_clean IS NULL OR city_clean<>city))) THEN RAISE EXCEPTION 'users: city transformation differs from provisional rule'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.users WHERE city_missing_token;
    SELECT expected_city_tokens INTO v_expected FROM expected_inputs WHERE table_name='users';
    IF v_expected IS NULL OR v_n <> v_expected THEN RAISE EXCEPTION 'users: known city issue drift'; END IF;
    IF EXISTS (SELECT order_id FROM stg.orders GROUP BY order_id HAVING order_id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'orders: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.orders;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='orders';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'orders: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.orders WHERE order_id<=0) THEN RAISE EXCEPTION 'orders.order_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.orders WHERE user_id<=0) THEN RAISE EXCEPTION 'orders.user_id: nonpositive key'; END IF;
    IF EXISTS (SELECT id FROM stg.order_items GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'order_items: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.order_items;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='order_items';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'order_items: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items WHERE id<=0) THEN RAISE EXCEPTION 'order_items.id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items WHERE order_id<=0) THEN RAISE EXCEPTION 'order_items.order_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items WHERE user_id<=0) THEN RAISE EXCEPTION 'order_items.user_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items WHERE product_id<=0) THEN RAISE EXCEPTION 'order_items.product_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items WHERE inventory_item_id<=0) THEN RAISE EXCEPTION 'order_items.inventory_item_id: nonpositive key'; END IF;
    IF EXISTS (SELECT id FROM stg.inventory_items GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'inventory_items: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.inventory_items;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='inventory_items';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'inventory_items: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.inventory_items WHERE id<=0) THEN RAISE EXCEPTION 'inventory_items.id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.inventory_items WHERE product_id<=0) THEN RAISE EXCEPTION 'inventory_items.product_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.inventory_items WHERE product_distribution_center_id<=0) THEN RAISE EXCEPTION 'inventory_items.product_distribution_center_id: nonpositive key'; END IF;
    IF EXISTS (SELECT id FROM stg.events GROUP BY id HAVING id IS NULL OR COUNT(*)>1) THEN RAISE EXCEPTION 'events: invalid primary key'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.events;
    SELECT expected_rows INTO v_expected FROM expected_inputs WHERE table_name='events';
    IF v_n <> v_expected THEN RAISE EXCEPTION 'events: row count differs from approved package'; END IF;
    IF EXISTS (SELECT 1 FROM stg.events WHERE id<=0) THEN RAISE EXCEPTION 'events.id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.events WHERE user_id<=0) THEN RAISE EXCEPTION 'events.user_id: nonpositive key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.events WHERE city_missing_token <> (LOWER(TRIM(city))='null') OR (city_missing_token AND city_clean IS NOT NULL) OR (NOT city_missing_token AND (city_clean IS NULL OR city_clean<>city))) THEN RAISE EXCEPTION 'events: city transformation differs from provisional rule'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.events WHERE city_missing_token;
    SELECT expected_city_tokens INTO v_expected FROM expected_inputs WHERE table_name='events';
    IF v_expected IS NULL OR v_n <> v_expected THEN RAISE EXCEPTION 'events: known city issue drift'; END IF;
    IF EXISTS (SELECT 1 FROM stg.products c LEFT JOIN stg.distribution_centers p ON c.distribution_center_id=p.id WHERE c.distribution_center_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'products.distribution_center_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.inventory_items c LEFT JOIN stg.products p ON c.product_id=p.id WHERE c.product_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'inventory_items.product_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.inventory_items c LEFT JOIN stg.distribution_centers p ON c.product_distribution_center_id=p.id WHERE c.product_distribution_center_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'inventory_items.product_distribution_center_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.orders c LEFT JOIN stg.users p ON c.user_id=p.id WHERE c.user_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'orders.user_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items c LEFT JOIN stg.orders p ON c.order_id=p.order_id WHERE c.order_id IS NOT NULL AND p.order_id IS NULL) THEN RAISE EXCEPTION 'order_items.order_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items c LEFT JOIN stg.users p ON c.user_id=p.id WHERE c.user_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'order_items.user_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items c LEFT JOIN stg.products p ON c.product_id=p.id WHERE c.product_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'order_items.product_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.order_items c LEFT JOIN stg.inventory_items p ON c.inventory_item_id=p.id WHERE c.inventory_item_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'order_items.inventory_item_id: orphan key'; END IF;
    IF EXISTS (SELECT 1 FROM stg.events c LEFT JOIN stg.users p ON c.user_id=p.id WHERE c.user_id IS NOT NULL AND p.id IS NULL) THEN RAISE EXCEPTION 'events.user_id: orphan key'; END IF;


    FOR r IN SELECT * FROM expected_money LOOP
        EXECUTE 'SELECT SUM(' || QUOTE_IDENT(r.column_name) || ') FROM stg.' || QUOTE_IDENT(r.table_name) INTO v_sum;
        IF v_sum IS NULL OR v_sum<>r.expected_sum THEN RAISE EXCEPTION 'Staging monetary reconciliation failed'; END IF;
    END LOOP;
    IF EXISTS(SELECT 1 FROM stg.orders o LEFT JOIN
          (SELECT order_id,COUNT(*) n FROM stg.order_items GROUP BY order_id) i ON i.order_id=o.order_id
          WHERE o.num_of_item<>COALESCE(i.n,0) OR o.num_of_item<=0) THEN
        RAISE EXCEPTION 'Order item counts disagree with orders';
    END IF;
    IF EXISTS(SELECT 1 FROM stg.order_items i JOIN stg.orders o ON o.order_id=i.order_id
              JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id
              WHERE i.user_id<>o.user_id OR i.product_id<>inv.product_id) THEN
        RAISE EXCEPTION 'Item user/product does not match parent';
    END IF;
    IF EXISTS(SELECT 1 FROM stg.order_items WHERE
        item_dates_comparable<>(created_at IS NOT NULL AND shipped_at IS NOT NULL)
        OR (item_dates_comparable AND (item_shipped_before_created IS NULL OR item_shipped_before_created<>(shipped_at<created_at)))
        OR (NOT item_dates_comparable AND item_shipped_before_created IS NOT NULL)) THEN
        RAISE EXCEPTION 'Item date flags do not match timestamps';
    END IF;
    SELECT COUNT(*) INTO v_n FROM stg.order_items WHERE item_shipped_before_created;
    SELECT expected_date_flags INTO v_expected FROM expected_inputs WHERE table_name='order_items';
    IF v_expected IS NULL OR v_n<>v_expected THEN RAISE EXCEPTION 'Known date issue count drift'; END IF;
    SELECT COUNT(*) INTO v_n FROM stg.order_items WHERE item_dates_comparable;
    SELECT expected_comparable INTO v_expected FROM expected_inputs WHERE table_name='order_items';
    IF v_expected IS NULL OR v_n<>v_expected THEN RAISE EXCEPTION 'Known date denominator drift'; END IF;

    -- Guard natural-key uniqueness BEFORE lookup/update. Redshift does not enforce PK/FK.
    IF EXISTS(SELECT user_id FROM dw.dim_users WHERE is_current GROUP BY user_id HAVING COUNT(*)>1)
       OR EXISTS(SELECT product_id FROM dw.dim_products GROUP BY product_id HAVING COUNT(*)>1)
       OR EXISTS(SELECT distribution_center_id FROM dw.dim_distribution_centers GROUP BY distribution_center_id HAVING COUNT(*)>1) THEN
        RAISE EXCEPTION 'Dimension natural-key uniqueness failed';
    END IF;
    DROP TABLE IF EXISTS tmp_user_source;
    CREATE TEMP TABLE tmp_user_source AS SELECT id AS user_id, first_name || ' ' || last_name AS full_name,
        email,age,CASE WHEN age BETWEEN 0 AND 17 THEN '<18' WHEN age BETWEEN 18 AND 25 THEN '18-25'
            WHEN age BETWEEN 26 AND 35 THEN '26-35' WHEN age BETWEEN 36 AND 50 THEN '36-50'
            WHEN age BETWEEN 51 AND 120 THEN '51+' ELSE NULL END::VARCHAR(20) AS age_group,
        gender,city_clean AS city,city_missing_token,state,country,postal_code,traffic_source FROM stg.users;
    DROP TABLE IF EXISTS tmp_user_changes;
    CREATE TEMP TABLE tmp_user_changes AS SELECT s.*, u.user_key AS old_user_key
      FROM tmp_user_source s LEFT JOIN dw.dim_users u ON u.user_id=s.user_id AND u.is_current
      WHERE u.user_key IS NULL OR (
CASE WHEN u.full_name=s.full_name OR (u.full_name IS NULL AND s.full_name IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.email=s.email OR (u.email IS NULL AND s.email IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.age=s.age OR (u.age IS NULL AND s.age IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.gender=s.gender OR (u.gender IS NULL AND s.gender IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.city=s.city OR (u.city IS NULL AND s.city IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.city_missing_token=s.city_missing_token OR (u.city_missing_token IS NULL AND s.city_missing_token IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.state=s.state OR (u.state IS NULL AND s.state IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.country=s.country OR (u.country IS NULL AND s.country IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.postal_code=s.postal_code OR (u.postal_code IS NULL AND s.postal_code IS NULL) THEN FALSE ELSE TRUE END OR
            CASE WHEN u.traffic_source=s.traffic_source OR (u.traffic_source IS NULL AND s.traffic_source IS NULL) THEN FALSE ELSE TRUE END
      );
    UPDATE dw.dim_users SET valid_to=p_observed_at,is_current=FALSE
      FROM tmp_user_changes c WHERE dw.dim_users.user_key=c.old_user_key;
    INSERT INTO dw.dim_users(user_id,full_name,email,age,age_group,gender,city,city_missing_token,state,country,
        postal_code,traffic_source,valid_from,valid_to,is_current,version_origin,observed_at,source_batch_id,rule_version)
    SELECT user_id,full_name,email,age,age_group,gender,city,city_missing_token,state,country,postal_code,traffic_source,
        CASE WHEN v_bootstrap THEN NULL::TIMESTAMPTZ ELSE p_observed_at END,NULL::TIMESTAMPTZ,TRUE,
        CASE WHEN v_bootstrap THEN 'BOOTSTRAP_SNAPSHOT' WHEN old_user_key IS NULL THEN 'OBSERVED_NEW' ELSE 'OBSERVED_CHANGE' END,
        p_observed_at,p_batch_id,p_rule_version FROM tmp_user_changes;

    -- Type 1 dimensions: null-safe comparisons, keys never regenerated for existing IDs.
    UPDATE dw.dim_products SET product_name=s.name,category=s.category,brand=s.brand,department=s.department,
        sku=s.sku,retail_price=s.retail_price,cost=s.cost,source_batch_id=p_batch_id,updated_at=p_observed_at
    FROM stg.products s WHERE dw.dim_products.product_id=s.id AND (
        CASE WHEN dw.dim_products.product_name=s.name OR (dw.dim_products.product_name IS NULL AND s.name IS NULL) THEN FALSE ELSE TRUE END
        OR CASE WHEN dw.dim_products.brand=s.brand OR (dw.dim_products.brand IS NULL AND s.brand IS NULL) THEN FALSE ELSE TRUE END
        OR dw.dim_products.category<>s.category OR dw.dim_products.department<>s.department OR dw.dim_products.sku<>s.sku
        OR dw.dim_products.retail_price<>s.retail_price OR dw.dim_products.cost<>s.cost);
    INSERT INTO dw.dim_products(product_id,product_name,category,brand,department,sku,retail_price,cost,source_batch_id,updated_at)
    SELECT s.id,s.name,s.category,s.brand,s.department,s.sku,s.retail_price,s.cost,p_batch_id,p_observed_at
      FROM stg.products s LEFT JOIN dw.dim_products d ON d.product_id=s.id WHERE d.product_key IS NULL;
    UPDATE dw.dim_distribution_centers SET dc_name=s.name,latitude=s.latitude,longitude=s.longitude,
        source_batch_id=p_batch_id,updated_at=p_observed_at
      FROM stg.distribution_centers s WHERE dw.dim_distribution_centers.distribution_center_id=s.id AND
        (dw.dim_distribution_centers.dc_name<>s.name OR dw.dim_distribution_centers.latitude<>s.latitude OR dw.dim_distribution_centers.longitude<>s.longitude);
    INSERT INTO dw.dim_distribution_centers(distribution_center_id,dc_name,latitude,longitude,source_batch_id,updated_at)
      SELECT s.id,s.name,s.latitude,s.longitude,p_batch_id,p_observed_at FROM stg.distribution_centers s
      LEFT JOIN dw.dim_distribution_centers d ON d.distribution_center_id=s.id WHERE d.distribution_center_key IS NULL;

    -- SCD invariants and overlap; NULL lower boundary belongs only to initial bootstrap.
    IF EXISTS(SELECT user_id FROM dw.dim_users GROUP BY user_id HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END)<>1)
       OR EXISTS(SELECT 1 FROM dw.dim_users WHERE is_current<>(valid_to IS NULL)
           OR (valid_from IS NULL AND version_origin<>'BOOTSTRAP_SNAPSHOT')
           OR (valid_from IS NOT NULL AND valid_to<=valid_from))
       OR EXISTS(SELECT 1 FROM dw.dim_users a JOIN dw.dim_users b ON a.user_id=b.user_id AND a.user_key<b.user_key
           WHERE (a.valid_from IS NULL OR b.valid_to IS NULL OR a.valid_from<b.valid_to)
             AND (b.valid_from IS NULL OR a.valid_to IS NULL OR b.valid_from<a.valid_to)) THEN
        RAISE EXCEPTION 'Invalid or overlapping SCD intervals';
    END IF;

    -- Calendar generator: 100,000 days, with an explicit guard instead of silent truncation.
    SELECT MIN(d),MAX(d) INTO v_min_date,v_max_date FROM (
        SELECT CAST(created_at AT TIME ZONE 'UTC' AS DATE) d FROM stg.orders UNION ALL
        SELECT CAST(shipped_at AT TIME ZONE 'UTC' AS DATE) FROM stg.orders UNION ALL
        SELECT CAST(delivered_at AT TIME ZONE 'UTC' AS DATE) FROM stg.orders UNION ALL
        SELECT CAST(returned_at AT TIME ZONE 'UTC' AS DATE) FROM stg.orders) dates;
    v_days := DATEDIFF(day,v_min_date,v_max_date);
    IF v_min_date IS NULL OR v_days>99999 THEN RAISE EXCEPTION 'Unsupported calendar range'; END IF;
    DROP TABLE IF EXISTS tmp_digits;
    CREATE TEMP TABLE tmp_digits AS SELECT 0 n UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4
        UNION ALL SELECT 5 UNION ALL SELECT 6 UNION ALL SELECT 7 UNION ALL SELECT 8 UNION ALL SELECT 9;
    DROP TABLE IF EXISTS tmp_calendar;
    CREATE TEMP TABLE tmp_calendar AS SELECT CAST(DATEADD(day,a.n+10*b.n+100*c.n+1000*d.n+10000*e.n,v_min_date) AS DATE) full_date
        FROM tmp_digits a CROSS JOIN tmp_digits b CROSS JOIN tmp_digits c CROSS JOIN tmp_digits d CROSS JOIN tmp_digits e
        WHERE a.n+10*b.n+100*c.n+1000*d.n+10000*e.n<=v_days;
    INSERT INTO dw.dim_date(date_key,full_date,day_of_week,day_name,day_of_month,month,month_name,quarter,year,is_weekend)
    SELECT TO_CHAR(c.full_date,'YYYYMMDD')::INTEGER,c.full_date,
        CASE WHEN DATE_PART(dow,c.full_date)=0 THEN 7 ELSE DATE_PART(dow,c.full_date)::SMALLINT END,
        TRIM(TO_CHAR(c.full_date,'Day')),DATE_PART(day,c.full_date)::SMALLINT,DATE_PART(month,c.full_date)::SMALLINT,
        TRIM(TO_CHAR(c.full_date,'Month')),DATE_PART(quarter,c.full_date)::SMALLINT,DATE_PART(year,c.full_date)::INTEGER,
        DATE_PART(dow,c.full_date) IN (0,6)
    FROM tmp_calendar c LEFT JOIN dw.dim_date d ON d.full_date=c.full_date WHERE d.date_key IS NULL;

    -- Preserve unmatched/ambiguous rows long enough to reject them, not silently inner-join them away.
    IF EXISTS(SELECT i.id FROM stg.order_items i JOIN stg.orders o ON o.order_id=i.order_id
        LEFT JOIN dw.dim_users u ON u.user_id=i.user_id
           AND (u.valid_from IS NULL OR o.created_at>=u.valid_from) AND (u.valid_to IS NULL OR o.created_at<u.valid_to)
        GROUP BY i.id HAVING COUNT(u.user_key)<>1) THEN
        RAISE EXCEPTION 'User as-of lookup must match exactly once; review late-arriving facts';
    END IF;
    DROP TABLE IF EXISTS tmp_fact_work;
    CREATE TEMP TABLE tmp_fact_work (LIKE dw.fact_sales);
    INSERT INTO tmp_fact_work(order_item_id,order_id,inventory_item_id,user_key,product_key,distribution_center_key,
        order_created_at,order_shipped_at,order_delivered_at,order_returned_at,order_date_key,shipped_date_key,delivered_date_key,returned_date_key,
        status,quantity,sale_price,product_cost,reference_retail_price,gross_profit,catalog_price_difference,discount_amount,
        shipping_duration_days,item_shipped_before_created,item_dates_comparable,source_batch_id,rule_version,loaded_at)
    SELECT i.id,i.order_id,i.inventory_item_id,u.user_key,p.product_key,dc.distribution_center_key,
        o.created_at,o.shipped_at,o.delivered_at,o.returned_at,
        TO_CHAR(o.created_at AT TIME ZONE 'UTC','YYYYMMDD')::INTEGER,
        TO_CHAR(o.shipped_at AT TIME ZONE 'UTC','YYYYMMDD')::INTEGER,
        TO_CHAR(o.delivered_at AT TIME ZONE 'UTC','YYYYMMDD')::INTEGER,
        TO_CHAR(o.returned_at AT TIME ZONE 'UTC','YYYYMMDD')::INTEGER,
        i.status,1,i.sale_price,inv.cost,inv.product_retail_price,
        CAST(i.sale_price-inv.cost AS DECIMAL(19,6)),CAST(inv.product_retail_price-i.sale_price AS DECIMAL(19,6)),NULL::DECIMAL(19,6),
        -- Exact positive HALF_UP to 1e-6 day: elapsed microseconds / 86400 gives millionths of a day.
        CASE WHEN o.shipped_at IS NOT NULL AND o.delivered_at>=o.shipped_at THEN
            CAST(FLOOR((DATEDIFF(microsecond,o.shipped_at,o.delivered_at)::DECIMAL(20,0)+43200)/86400)
                 /1000000.0 AS DECIMAL(18,6)) ELSE NULL::DECIMAL(18,6) END,
        i.item_shipped_before_created,i.item_dates_comparable,p_batch_id,p_rule_version,p_observed_at
    FROM stg.order_items i JOIN stg.orders o ON o.order_id=i.order_id
    JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id
    JOIN dw.dim_products p ON p.product_id=i.product_id
    JOIN dw.dim_distribution_centers dc ON dc.distribution_center_id=inv.product_distribution_center_id
    JOIN dw.dim_users u ON u.user_id=i.user_id
       AND (u.valid_from IS NULL OR o.created_at>=u.valid_from) AND (u.valid_to IS NULL OR o.created_at<u.valid_to);

    SELECT COUNT(*) INTO v_n FROM tmp_fact_work;
    SELECT COUNT(*) INTO v_expected FROM stg.order_items;
    IF v_n<>v_expected OR EXISTS(SELECT order_item_id FROM tmp_fact_work GROUP BY 1 HAVING COUNT(*)>1) THEN
        RAISE EXCEPTION 'Fact grain/row count changed after joins';
    END IF;
    IF EXISTS(SELECT 1 FROM tmp_fact_work f JOIN stg.order_items i ON i.id=f.order_item_id
        JOIN stg.inventory_items inv ON inv.id=i.inventory_item_id WHERE f.sale_price<>i.sale_price OR f.product_cost<>inv.cost
        OR f.reference_retail_price<>inv.product_retail_price OR f.quantity<>1 OR f.discount_amount IS NOT NULL
        OR f.gross_profit<>CAST(i.sale_price-inv.cost AS DECIMAL(19,6))
        OR f.catalog_price_difference<>CAST(inv.product_retail_price-i.sale_price AS DECIMAL(19,6))) THEN
        RAISE EXCEPTION 'Fact monetary/control values differ from staging';
    END IF;
    IF EXISTS(SELECT 1 FROM tmp_fact_work f
        LEFT JOIN dw.dim_date a ON a.date_key=f.order_date_key LEFT JOIN dw.dim_date b ON b.date_key=f.shipped_date_key
        LEFT JOIN dw.dim_date c ON c.date_key=f.delivered_date_key LEFT JOIN dw.dim_date d ON d.date_key=f.returned_date_key
        WHERE a.date_key IS NULL OR (f.shipped_date_key IS NOT NULL AND b.date_key IS NULL)
           OR (f.delivered_date_key IS NOT NULL AND c.date_key IS NULL) OR (f.returned_date_key IS NOT NULL AND d.date_key IS NULL)) THEN
        RAISE EXCEPTION 'Fact date key not found';
    END IF;
    IF EXISTS(SELECT user_key FROM dw.dim_users GROUP BY 1 HAVING COUNT(*)>1)
       OR EXISTS(SELECT product_key FROM dw.dim_products GROUP BY 1 HAVING COUNT(*)>1)
       OR EXISTS(SELECT distribution_center_key FROM dw.dim_distribution_centers GROUP BY 1 HAVING COUNT(*)>1)
       OR EXISTS(SELECT date_key FROM dw.dim_date GROUP BY 1 HAVING COUNT(*)>1)
       OR EXISTS(SELECT full_date FROM dw.dim_date GROUP BY 1 HAVING COUNT(*)>1) THEN
        RAISE EXCEPTION 'Duplicate dimension key';
    END IF;

    -- Publish only after every check. No TRUNCATE/COMMIT inside this atomic call.
    DELETE FROM dw.fact_sales;
    INSERT INTO dw.fact_sales SELECT * FROM tmp_fact_work;
    INSERT INTO etl.batch_ledger VALUES(p_batch_id,p_package_hash,p_observed_at,p_schema_version,p_rule_version,GETDATE(),v_n,'SUCCEEDED');
    INSERT INTO etl.batch_inputs SELECT p_batch_id,table_name,file_sha256,expected_rows,manifest_url FROM expected_inputs;
    INSERT INTO etl.batch_checks VALUES(p_batch_id,'staging_integrity_and_money','PASS',NULL,'Seven counts, PK/FK, 5 monetary controls and flags checked');
    INSERT INTO etl.batch_checks VALUES(p_batch_id,'fact_grain_and_values','PASS',v_n,'One item per row; exact source money and dimensions/date references');
    INSERT INTO etl.batch_checks SELECT p_batch_id,'city_null_users','KNOWN_ISSUE',COUNT(*),'provisional-v1; source confirmation pending' FROM stg.users WHERE city_missing_token;
    INSERT INTO etl.batch_checks SELECT p_batch_id,'city_null_events','KNOWN_ISSUE',COUNT(*),'provisional-v1; source confirmation pending' FROM stg.events WHERE city_missing_token;
    INSERT INTO etl.batch_checks SELECT p_batch_id,'item_date_order','KNOWN_ISSUE',COUNT(*),'provisional-v1; source confirmation pending' FROM stg.order_items WHERE item_shipped_before_created;
    INSERT INTO etl.batch_checks SELECT p_batch_id,'order_shipping_date_order',CASE WHEN COUNT(*)=0 THEN 'PASS' ELSE 'WARN' END,
        COUNT(*),'shipping_duration_days remains NULL when delivered before shipped' FROM stg.orders WHERE delivered_at<shipped_at;
    INSERT INTO etl.batch_attempts VALUES(p_batch_id,GETDATE(),'SUCCEEDED','Published atomically; known issues retained');

EXCEPTION WHEN OTHERS THEN
    -- In default mode Redshift rolls back the failed transaction, logs in a new
    -- transaction, commits the handler, then automatically rethrows the error.
    INSERT INTO etl.batch_attempts(batch_id, attempted_at, status, detail)
    VALUES (p_batch_id, GETDATE(), 'FAILED', LEFT(SQLERRM, 4000));
END;
$$ LANGUAGE plpgsql;
