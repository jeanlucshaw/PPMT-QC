# Module ppmt
Software to streamline processing of the DFO thermograph network data in the Gulf of 
St. Lawrence (Québec region).

## History
The Department of Fisheries and Oceans Canada (DFO) supports the Atlantic Zone Monitoring
Program (AZMP), in the context of which a network of coastal temperature and salinity sensors
(referred to here as thermographs) are being deployed on an annual basis at the same locations.
Beginning in 1993, this initiative pre-dates the AZMP but is now integrated into its operations.

Several data analysts have been responsible for the quality assurance and quality control of
the thermograph data over the years, each using their own set of tools, but these are often
not transferable to the next data analyst because of software license and tool documentation
issues. The objective of this module is to provide a reusable tool in a centralized location
such that maintenance of this program is less affected by employee turnover and mobility.

## Module installation
The intended use of this module is to be cloned onto a DFO work computer connected to the
DFO local network either on site or through VPN, and used either from the `cmd` command line,
from some python shell (e.g., Python, Anaconda Prompt, iPython) or inside an IDE.

## Workflow

### Field technician responsibilities
Once they have recovered the deployed thermographs, the field technician(s) extract the data
resulting in `.cnv` and `.csv` files and stored them in the shared folder
```
S:\Soutien technique DAISS\PPMT\Donnees\non traite
```
which is accessible to the required DFO staff when connected to the DFO network. They then proceed
to check each device for sensor drift by calibration against a conductivity standard or calibration
in a water tank of known temperature. The resulting calibrations are noted in Excel (`.xls`)
spreadsheets and save in one of the following locations
```
S:\Etalon\Équipement Océanographique\Seabird\SBE-56\*\*.xlsx
S:\Etalon\Équipement Océanographique\Seabird\SBE-37\V1\*\*.xlsx
S:\Etalon\Équipement Océanographique\Seabird\SBE-37\V1\*\*\*.xlsx
S:\Etalon\Équipement Océanographique\Seabird\SBE-37\V2\*\*.xlsx
S:\Etalon\Équipement Océanographique\Seabird\SBE-37\V2\*\*\*.xlsx
```
where the asterisk (`*`) denotes the globing wildcard. This means that SBE-37 calibration files will
be found 1 or 2 layers deep into the V1 or V2 directories. If new calibration files are saved in
other locations, or other directory tree depths, it is best to advise the data analyst assigned
to this project. Calibration files have varying naming conventions, but must be saved as `.xls` files
and their names must contain the device's serial number for this software to function normally.

The field technician(s) also maintain a device inventory file series found in
```
S:\Soutien technique DAISS\PPMT\Liste suivi thermographe
```
and containing deployment metadata in relation to the device's serial number. The columns of this file
which must be filled in for this software to function normally are:
* `profondeur des instruments`;
* `Code unique`;
* `Code unique instrument`;
* `INSTRUMENTS` (SBE 56 or SBE 37);
* `Date d'installation des instruments`;
* `Date de récupération des instruments`.

Note that the inventory files follow the naming convention `suivi(year of deployment; YYYY).xlsx` and that
filling in the bottom section ('Mouillages au fond') has historically been the data analyst's responsability.

### Data analyst responsibilities



### Data manager responsibilities

## Examples

### Terminal (`cmd`) operation

### Interactive python shell

### IDE operation

## References
Pettigrew, B., Gilbert, D. and Desmarais R. 2016. Thermograph network in the Gulf
of St. Lawrence. Can. Tech. Rep. Hydrogr. Ocean Sci. 311: vi + 77 p.
