-- create_tables_external.sql
-- Skema delapan tabel dataset eksternal untuk cross-dataset validation.
-- Tanpa GO: dijalankan per pernyataan melalui import_external_to_sql.py.

-- UCI Online Retail II — kolom filter: Quantity >= 6

CREATE TABLE dbo.UCI5k (
    ID           NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq          INT           NOT NULL,
    Invoice      NVARCHAR(20)  NOT NULL,
    StockCode    NVARCHAR(20)  NOT NULL,
    Description  NVARCHAR(200) NOT NULL,
    Country      NVARCHAR(50)  NOT NULL,
    InvoiceDate  DATE          NOT NULL,
    Quantity     INT           NOT NULL,
    Price        DECIMAL(10,2) NOT NULL,
    CustomerID   INT           NOT NULL
);
CREATE UNIQUE INDEX IX_UCI5k_Seq ON dbo.UCI5k(Seq);
CREATE INDEX IX_UCI5k_Quantity ON dbo.UCI5k(Quantity);

CREATE TABLE dbo.UCI10k (
    ID           NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq          INT           NOT NULL,
    Invoice      NVARCHAR(20)  NOT NULL,
    StockCode    NVARCHAR(20)  NOT NULL,
    Description  NVARCHAR(200) NOT NULL,
    Country      NVARCHAR(50)  NOT NULL,
    InvoiceDate  DATE          NOT NULL,
    Quantity     INT           NOT NULL,
    Price        DECIMAL(10,2) NOT NULL,
    CustomerID   INT           NOT NULL
);
CREATE UNIQUE INDEX IX_UCI10k_Seq ON dbo.UCI10k(Seq);
CREATE INDEX IX_UCI10k_Quantity ON dbo.UCI10k(Quantity);

CREATE TABLE dbo.UCI50k (
    ID           NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq          INT           NOT NULL,
    Invoice      NVARCHAR(20)  NOT NULL,
    StockCode    NVARCHAR(20)  NOT NULL,
    Description  NVARCHAR(200) NOT NULL,
    Country      NVARCHAR(50)  NOT NULL,
    InvoiceDate  DATE          NOT NULL,
    Quantity     INT           NOT NULL,
    Price        DECIMAL(10,2) NOT NULL,
    CustomerID   INT           NOT NULL
);
CREATE UNIQUE INDEX IX_UCI50k_Seq ON dbo.UCI50k(Seq);
CREATE INDEX IX_UCI50k_Quantity ON dbo.UCI50k(Quantity);

CREATE TABLE dbo.UCI100k (
    ID           NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq          INT           NOT NULL,
    Invoice      NVARCHAR(20)  NOT NULL,
    StockCode    NVARCHAR(20)  NOT NULL,
    Description  NVARCHAR(200) NOT NULL,
    Country      NVARCHAR(50)  NOT NULL,
    InvoiceDate  DATE          NOT NULL,
    Quantity     INT           NOT NULL,
    Price        DECIMAL(10,2) NOT NULL,
    CustomerID   INT           NOT NULL
);
CREATE UNIQUE INDEX IX_UCI100k_Seq ON dbo.UCI100k(Seq);
CREATE INDEX IX_UCI100k_Quantity ON dbo.UCI100k(Quantity);

-- Olist — kolom filter: FreightValue >= 20

CREATE TABLE dbo.Olist5k (
    ID             NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq            INT           NOT NULL,
    OrderID        NVARCHAR(32)  NOT NULL,
    ProductID      NVARCHAR(32)  NOT NULL,
    Category       NVARCHAR(100) NOT NULL,
    CustomerState  NVARCHAR(2)   NOT NULL,
    PurchaseDate   DATE          NOT NULL,
    Price          DECIMAL(10,2) NOT NULL,
    FreightValue   DECIMAL(10,2) NOT NULL,
    ProductWeight  INT           NOT NULL
);
CREATE UNIQUE INDEX IX_Olist5k_Seq ON dbo.Olist5k(Seq);
CREATE INDEX IX_Olist5k_FreightValue ON dbo.Olist5k(FreightValue);

CREATE TABLE dbo.Olist10k (
    ID             NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq            INT           NOT NULL,
    OrderID        NVARCHAR(32)  NOT NULL,
    ProductID      NVARCHAR(32)  NOT NULL,
    Category       NVARCHAR(100) NOT NULL,
    CustomerState  NVARCHAR(2)   NOT NULL,
    PurchaseDate   DATE          NOT NULL,
    Price          DECIMAL(10,2) NOT NULL,
    FreightValue   DECIMAL(10,2) NOT NULL,
    ProductWeight  INT           NOT NULL
);
CREATE UNIQUE INDEX IX_Olist10k_Seq ON dbo.Olist10k(Seq);
CREATE INDEX IX_Olist10k_FreightValue ON dbo.Olist10k(FreightValue);

CREATE TABLE dbo.Olist50k (
    ID             NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq            INT           NOT NULL,
    OrderID        NVARCHAR(32)  NOT NULL,
    ProductID      NVARCHAR(32)  NOT NULL,
    Category       NVARCHAR(100) NOT NULL,
    CustomerState  NVARCHAR(2)   NOT NULL,
    PurchaseDate   DATE          NOT NULL,
    Price          DECIMAL(10,2) NOT NULL,
    FreightValue   DECIMAL(10,2) NOT NULL,
    ProductWeight  INT           NOT NULL
);
CREATE UNIQUE INDEX IX_Olist50k_Seq ON dbo.Olist50k(Seq);
CREATE INDEX IX_Olist50k_FreightValue ON dbo.Olist50k(FreightValue);

CREATE TABLE dbo.Olist100k (
    ID             NVARCHAR(36)  NOT NULL PRIMARY KEY,
    Seq            INT           NOT NULL,
    OrderID        NVARCHAR(32)  NOT NULL,
    ProductID      NVARCHAR(32)  NOT NULL,
    Category       NVARCHAR(100) NOT NULL,
    CustomerState  NVARCHAR(2)   NOT NULL,
    PurchaseDate   DATE          NOT NULL,
    Price          DECIMAL(10,2) NOT NULL,
    FreightValue   DECIMAL(10,2) NOT NULL,
    ProductWeight  INT           NOT NULL
);
CREATE UNIQUE INDEX IX_Olist100k_Seq ON dbo.Olist100k(Seq);
CREATE INDEX IX_Olist100k_FreightValue ON dbo.Olist100k(FreightValue);