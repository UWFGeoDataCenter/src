CREATE TABLE [src_db].[dbo].[src_prod]([OBJECTID] INT,[BuildingIdent] varchar(100),[Description] varchar(50),[Class] varchar(3),[TypeCode] INT, [GlobalID] varchar(50))

UPDATE [src_db].[dbo].src_prod SET [Class]='Yes' WHERE [BuildingIdent]='99'
UPDATE [src_db].[dbo].src_prod SET [Class]='Yes' WHERE [BuildingIdent]='960'