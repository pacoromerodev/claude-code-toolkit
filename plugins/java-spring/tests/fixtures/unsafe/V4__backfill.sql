-- No WHERE: locks every row for as long as the table is big.
UPDATE orders SET channel = 'WEB';
