# ข้อมูลต้นทาง (ไม่นำ CSV ขึ้น Git)

ขอชุดข้อมูล TheLook E-Commerce จากผู้ดูแลโครงการ แล้ววาง CSV ทั้ง 7 ไฟล์ในโฟลเดอร์นี้:

- distribution_centers.csv
- products.csv
- users.csv
- orders.csv
- order_items.csv
- inventory_items.csv
- events.csv

ใช้ชุดเดียวกับที่ตรวจไว้ใน `code/dq_known_issues_baseline.json` (อ้างจาก project root) ซึ่งมี source hashes กำกับ หากเปลี่ยนชุดข้อมูล ให้ตรวจความต่างและทบทวน baseline ก่อน ห้ามเปลี่ยน baseline เพียงเพื่อให้ test ผ่าน

เก็บไฟล์ raw เดิม ไม่แก้ทับ CSV มีข้อมูลระดับแถว เช่น ชื่อ อีเมลและที่อยู่ จึงไม่นำขึ้น repository ชุดข้อมูลและสิทธิ์แจกจ่ายต้องตรวจจากต้นทาง ไม่ได้แนบหรือดาวน์โหลดอัตโนมัติใน repository นี้

# ไม่ใช้ events แล้ว - ขิม