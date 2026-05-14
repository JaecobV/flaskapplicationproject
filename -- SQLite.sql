-- SQLite
ALTER TABLE Parts
ADD COLUMN Image TEXT;

UPDATE Parts
SET Image = 'Intel_Core_i5_12400F_1.webp'
WHERE Part_ID = 1;