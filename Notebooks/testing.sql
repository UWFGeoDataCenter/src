CREATE TABLE [src_db].[dbo].[src_prod]([FID] INT,[BuildingID] varchar(100),[Description] varchar(50),[Classrooms] varchar(3),[TypeCode] INT, [X] FLOAT, [Y] FLOAT, [Email] varchar(50))

UPDATE [src_db].[dbo].src_prod SET [Classrooms]='No' WHERE [BuildingID]='58A'
UPDATE [src_db].[dbo].src_prod SET [Classrooms]='No' WHERE [BuildingID]='4'

DELETE from [src_db].[dbo].[src_prod] WHERE [FID] = '145'