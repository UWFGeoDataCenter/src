-- ================================================
--TEST
-- ================================================
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
ALTER PROCEDURE GetRecordByGlobalID 
	@global_id		varchar(50) = Null
AS
BEGIN
	SET NOCOUNT ON;
    -- Insert statements for procedure here
	SELECT * FROM dbo.src_prod WHERE [GlobalID] = @global_id
	--SELECT @global_id
END
GO
