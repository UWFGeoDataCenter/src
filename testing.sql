SELECT * FROM [src_db].[dbo].[src_temp]
SELECT * FROM [src_db].[dbo].[src_prod]

DELETE FROM [src_db].[dbo].[src_prod]

/*Insert test record in temp*/
INSERT INTO [dbo].[src_temp](OBJECTID, 
	BuildingIdent,Description,Class,TypeCode,GlobalID)  
    VALUES
	(420, 
	456,'NEW ONE','Yes',3,'b0303dd4-80ad-42cb-9a0b-7b0422d42808') 

INSERT INTO [dbo].[src_prod](OBJECTID, 
BuildingIdent,Description,Class,TypeCode,GlobalID)
SELECT * FROM [dbo].[src_temp] UNION  
SELECT * FROM [dbo].[src_prod] EXCEPT  
SELECT * FROM [dbo].[src_temp] INTERSECT SELECT * FROM [dbo].[src_prod]

EXEC [dbo].[GetRecordByGlobalID] '90f0da92-94c4-4dfa-bfe3-19498d3bf4c5'