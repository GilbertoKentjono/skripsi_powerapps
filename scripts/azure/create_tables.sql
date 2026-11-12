-- ============================================================
-- create_tables.sql
-- Membuat 5 tabel pengujian di Azure SQL (db-skripsi)
-- Jalankan lewat: Azure Portal > db-skripsi > Query editor (preview)
--
-- Struktur mengikuti skema 9 atribut, disamakan dengan tabel
-- Dataverse agar komparasi RM2 bersifat fair.
-- ============================================================

-- ---------- 5.000 record ----------
CREATE TABLE TestDataset5k (
    ID              NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Nama            NVARCHAR(100) NULL,
    Email           NVARCHAR(100) NULL,
    Wilayah         NVARCHAR(50)  NULL,
    KategoriProduk  NVARCHAR(50)  NULL,
    Tanggal         DATE          NULL,
    JumlahTransaksi INT           NULL,
    Status          NVARCHAR(20)  NULL,
    Rating          TINYINT       NULL,
    Seq INT NOT NULL
);
CREATE INDEX IX_TestDataset5k_Status ON TestDataset5k(Status);
CREATE UNIQUE INDEX IX_TestDataset5k_Seq ON dbo.TestDataset5k(Seq);

-- ---------- 10.000 record ----------
CREATE TABLE TestDataset10k (
    ID              NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Nama            NVARCHAR(100) NULL,
    Email           NVARCHAR(100) NULL,
    Wilayah         NVARCHAR(50)  NULL,
    KategoriProduk  NVARCHAR(50)  NULL,
    Tanggal         DATE          NULL,
    JumlahTransaksi INT           NULL,
    Status          NVARCHAR(20)  NULL,
    Rating          TINYINT       NULL,
        Seq INT NOT NULL

);
CREATE INDEX IX_TestDataset10k_Status ON TestDataset10k(Status);
CREATE UNIQUE INDEX IX_TestDataset10k_Seq ON dbo.TestDataset10k(Seq);

-- ---------- 25.000 record (HOLDOUT) ----------
CREATE TABLE TestDataset25k (
    ID              NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Nama            NVARCHAR(100) NULL,
    Email           NVARCHAR(100) NULL,
    Wilayah         NVARCHAR(50)  NULL,
    KategoriProduk  NVARCHAR(50)  NULL,
    Tanggal         DATE          NULL,
    JumlahTransaksi INT           NULL,
    Status          NVARCHAR(20)  NULL,
    Rating          TINYINT       NULL,
        Seq INT NOT NULL

);
CREATE INDEX IX_TestDataset25k_Status ON TestDataset25k(Status);
CREATE UNIQUE INDEX IX_TestDataset25k_Seq ON dbo.TestDataset25k(Seq);

-- ---------- 50.000 record ----------
CREATE TABLE TestDataset50k (
    ID              NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Nama            NVARCHAR(100) NULL,
    Email           NVARCHAR(100) NULL,
    Wilayah         NVARCHAR(50)  NULL,
    KategoriProduk  NVARCHAR(50)  NULL,
    Tanggal         DATE          NULL,
    JumlahTransaksi INT           NULL,
    Status          NVARCHAR(20)  NULL,
    Rating          TINYINT       NULL,
        Seq INT NOT NULL

);
CREATE INDEX IX_TestDataset50k_Status ON TestDataset50k(Status);
CREATE UNIQUE INDEX IX_TestDataset50k_Seq ON dbo.TestDataset50k(Seq);

-- ---------- 100.000 record ----------
CREATE TABLE TestDataset100k (
    ID              NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Nama            NVARCHAR(100) NULL,
    Email           NVARCHAR(100) NULL,
    Wilayah         NVARCHAR(50)  NULL,
    KategoriProduk  NVARCHAR(50)  NULL,
    Tanggal         DATE          NULL,
    JumlahTransaksi INT           NULL,
    Status          NVARCHAR(20)  NULL,
    Rating          TINYINT       NULL,
        Seq INT NOT NULL

);
CREATE INDEX IX_TestDataset100k_Status ON TestDataset100k(Status);
CREATE UNIQUE INDEX IX_TestDataset100k_Seq ON dbo.TestDataset100k(Seq);

-- ============================================================
-- Verifikasi setelah CREATE:
-- SELECT name FROM sys.tables ORDER BY name;
-- ============================================================
