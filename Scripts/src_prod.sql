USE [src_db]
GO

/****** Object:  Table [dbo].[src_prod]    Script Date: 5/28/2019 2:16:12 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

SET ANSI_PADDING ON
GO

CREATE TABLE [dbo].[src_prod](
	[FID] [int] NULL,
	[BuildingID] [varchar](100) NULL,
	[Description] [varchar](50) NULL,
	[Classrooms] [varchar](3) NULL,
	[TypeCode] [int] NULL,
	[X] [float] NULL,
	[Y] [float] NULL,
	[Email] [varchar](50) NULL
) ON [PRIMARY]

GO

SET ANSI_PADDING OFF
GO

