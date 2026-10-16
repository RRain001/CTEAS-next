Integrated Global Radiosonde Archive (IGRA) Version 2.2 Readme File 


Last updated: 04 September 2025


---------------------
Notes:
---------------------


1. This readme file is formatted for viewing in a text editor such as
   Windows Notepad or similar Linux-based editor.


2. The below information applies to versions 2.0 to 2.2 of IGRA.




------------------------------------------------------------------------
TABLE OF CONTENTS
------------------------------------------------------------------------


I.     OVERVIEW
II.    WHAT'S NEW IN IGRA 2.2
III.   DOWNLOAD QUICK START
IV.    CONTENTS OF FTP DIRECTORY
V.     CONTENTS OF WEB-ACCESSIBLE FOLDER
--------------------------------------------------------------------------------


------------------------------------------------------------------------
I. OVERVIEW
------------------------------------------------------------------------


This file provides guidance for how to navigate the FTP directory for 
Integrated Global Radiosonde Archive (IGRA). It provides a brief overview of 
what is new in IGRA 2.2, step-by-step instructions for downloading desired data 
and metadata, and an explanation of the contents of the directory and 
all of its subdirectories.
The formats of the various types of files available are described in 
separate documents.


As of February 2023, IGRA 2.2 replaces IGRA 2.0 as NCEI's baseline 
upper-air dataset.


Send any feedback to the IGRA Team at ncei.igra@noaa.gov.


-----------------------------------------------------------------------
II. WHAT'S NEW IN IGRA 2.2
------------------------------------------------------------------------


Following is a summary of what is new and different in IGRA 2.2 compared to
IGRA 2.0.


  - The NCEI/NCEP GTS record in Traditional Alphanumeric Code (TAC) 
    has been augmented with reports received in the newer Binary Universal 
    Form for the Representation of meteorological data (BUFR). This allows 
    data in IGRA to remain up-to-date as an increasing number of 
    stations switch to transmitting radiosonde reports via the Global 
    Telecommunication System (GTS). BUFR reports collected at the National 
    Weather Service's Telecommunications Gateway (NWSTG) and at 
    the European Centre for Medium-Range Weather Forecasts (ECMWF) 
    have been added as supplemental sources to the TAC GTS for each 
    station-day for which no TAC GTS reports are available and either
    NWSTG or ECMWF data are available. The filled-in soundings
    have been down-sampled from the typically high resolution of native 
    BUFR reports to the standard and significant levels that are consistent 
    with the historical record. For additional details, see the IGRA 
    Product Description Document located in the same folder as this 
    readme file. 

  - The OSCAR metadata source has been implemented in IGRA 2.2.  This is
    the primary metadata source now as the WMO Pub 9 metadata is no longer
    being updated.


  - The previous Dataset Description (igra2-dataset-description.pdf) has 
    been reworked into a high-level Product Description 
    (igra2-product-description.pdf) and more detailed Product Description 
    Supplement (igra2-product-description-supplement.pdf).


  - IGRA data can now be accessed in two ways. FTP access continues to be 
    available at https://www.ncei.noaa.gov/pub/data/igra/ 
    (see Section IV below for the file structure). 
    It is best used from Linux consoles or FTP clients as an increasing 
    number of browsers do not support access to FTP. An alternate 
    direct-download        location that also works within browsers can be found 
    in the web-accessible folder at 
    https://www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/ (see 
    Section V below). 


  - No changes have been made to the directory structure, file names, 
    or file formats.




------------------------------------------------------------------------
III. DOWNLOAD QUICK START
------------------------------------------------------------------------


Start by downloading "igra2-station-list.txt", which has metadata for all stations
in the dataset. You can find this file in the same location where you found this README
file. See the next two sections for details on file locations.


Then, to find and download the data for a specific station, proceed
as follows:


  - Find the station's name in "igra2-station-list.txt" and note its station
    identification code (e.g., Key West is "USM00072201").


  - Decide which of the following types of data you desire, navigate
    to the appropriate subdirectory, and download the desired 
    ZIP-compressed data file(s) and associated format documentation. 


    For individual soundings for the full period of record, go to
      subdirectory data-por and download the file containing the desired
     station ID in its filename (e.g., USM00072201-data.txt).
   For individual soundings from this year only, go to the data-y2d/ subdirectory and
     download the file containing the desired station ID in its filename.
   For period-of-record sounding-derived moisture, stability, and other 
     parameters, go to subdirectory derived-por/ and download the file whose name
     contains the desired station ID (e.g., USM00072201-drvd.txt).
   For monthly means for the full period of record, go to subdirectory 
     monthly-por/ download the file(s) for the desired variable and 
     nominal hour (e.g., temp_00z-mly.txt.zip for 0000 UTC temperature).
   For monthly means for only the last calendar month, go to 
     monthly-upd/ and download the file(s) for the desired variable 
     and nominal hour.
  
  - Uncompress the downloaded file using an uncompressing software (e.g., 
    7-Zip or winzip under Windows or the "gunzip" command under Linux).




------------------------------------------------------------------------
IV. CONTENTS OF FTP DIRECTORY (ftp.ncei.noaa.gov/pub/data/igra/)
------------------------------------------------------------------------


---------------------------------
Main level (ftp.ncei.noaa.gov/pub/data/igra/):
---------------------------------


data/                                      contains IGRA 2.2 sounding data files.
derived/                            contains IGRA 2.2 derived sounding parameters.
history/                            contains IGRA 2.2 station history information.
monthly/                            contains IGRA 2.2 monthly means 
v1/related/                                contains raw high-resolution BUFR radiosonde data


igra2-country-list.txt
    a list of country codes used in IGRA 2 station identifiers.
igra2-list-format.txt
    the description of the format of the IGRA 2 station list.
igra2-product-description.txt
    provides high-level documentation of IGRA
igra2-product-description-supplement.txt
    provides detailed technical documentation of IGRA
igra2-station-list.txt
    the list of all IGRA 2 stations and their name, location, period of    record, and number of
    soundings
igra2-readme.txt
    this file.
igra2-us-states.txt
    a list of all two-letter state codes shown in the IGRA 2 station list
status.txt 
    notes on the current status of IGRA 
                                
---------------------------------
Subdirectory data/ (pub/data/igra/data/):
---------------------------------


data-por/                        contains sounding data for the full period 
                                of record.
data-y2d/                        contains sounding data since January 1 
                                of the current or previous year.
igra2-data-format.txt                is the description of the format of the 
                                sounding data files.


---------------------------------
Subdirectory derived/ (pub/data/igra/derived/):
---------------------------------


derived-por/                        contains sounding-derived parameters for the full period of
record.
igra2-derived-format.txt        is the description of the format of the
                                sounding-derived parameter files.


---------------------------------
Subdirectory history/ (pub/data/igra/history/):
---------------------------------


igra2-metadata.txt                is documented station history information 
                                for IGRA 2 stations.
igra2-metadata-readme.txt        is a description of the format and origin of
                                the documented station history information.
wmo-history.txt                        is a description of the format of the WMO 
                                instrument code history files.
wmo-sonde-history.txt                is a list of the radiosonde codes extracted 
                                from GTS messages received at NCDC.
wmo-wndeq-history.txt                is a list of the measurement equipment codes 
                                extracted from GTS messages received at NCDC.


---------------------------------
Subdirectory monthly/ (pub/data/igra/monthly/):
---------------------------------


monthly-por/                        contains monthly means for the full period of 
                                record.
monthly-upd/                        contains monthly means for the last available 
                                month.
igra2-monthly-format.txt        is the description of the format of the
                                monthly-mean files.




------------------------------------------------------------------------
IV. CONTENTS OF WEB-ACCESSIBLE FOLDER
------------------------------------------------------------------------


---------------------------------
Main level (www.ncei.noaa.gov/data/integrated-global-radiosonde-archive/):
---------------------------------


access/                contains IGRA data files intended for public access
archive/        contains IGRA tar files as stored in NCEI's archive
doc/                contains documentation files


---------------------------------
Essential Metadata and Documentation
---------------------------------


doc/igra2-country-list.txt                is a list of country codes used in IGRA 2
                                station identifiers.
doc/igra2-list-Format.txt                is the description of the format of the IGRA 2
                                station list.
doc/igra2-station-list.txt                is the list of all IGRA 2 stations and their
                                name, location, period ofrecord, and 
                                number of soundings.
doc/igra2-readme.txt                is this file.
doc/igra2-us-states.txt                is a list of all two-letter state codes shown
                                in the IGRA 2 station list.
doc/status.txt                      notes on the current status of IGRA's 


data/                                contains IGRA 2.2 sounding data files.
derived/                        contains IGRA 2.2 derived sounding parameters.
history/                        contains IGRA 2.2 station history information.
monthly/                        contains IGRA 2.2 monthly means 
                                online files
---------------------------------
For Access to Sounding Data
---------------------------------


access/data-por/                        contains sounding data for the full period 
                                of record.
access/data-y2d/                        contains sounding data since January 1 
                                of the current or previous year.
doc/igra2-data-format.txt                is the description of the format of the 
                                sounding data files.


---------------------------------
Subdirectory derived/ (pub/data/igra/derived/):
---------------------------------


access/derived-por/                        contains sounding-derived parameters for the 
    full period of record.
doc/igra2-derived-format.txt        is the description of the format of the
    sounding-derived parameter files.


---------------------------------
For Accessing Monthly Means
---------------------------------


access/monthly-por/                        contains monthly means for the full period of 
                                record.
access/monthly-upd/                        contains monthly means for the last available 
                                month.
doc/igra2-monthly-format.txt        is the description of the format of the 
    monthly mean files.


---------------------------------
For Accessing Station History Information
---------------------------------


doc/igra2-metadata.txt                is documented station history information 
                                for IGRA 2 stations.
doc/igra2-metadata-readme.txt        is a description of the format and origin of
                                the documented station history information.
doc/wmo-history.txt                        is a description of the format of the WMO 
                                instrument code history files.
doc/wmo-sonde-history.txt                is a list of the radiosonde codes extracted 
                                from GTS messages received at NCDC.
doc/wmo-wndeq-history.txt                is a list of the measurement equipment codes 
                                extracted from GTS messages received at NCDC.