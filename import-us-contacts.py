"""
Import US law enforcement contacts - state police, FBI field offices, DEA, ATF, USMS.
"""

import sqlcipher3
from pathlib import Path

# Connect
pw = None
with open('.env') as f:
    for line in f:
        line = line.strip()
        if line.startswith('EMAIL_DB_PASSWORD='):
            pw = line.split('=', 1)[1].strip().strip('"').strip("'")
            break

db = sqlcipher3.connect(str(Path('leads.db')))
db.row_factory = sqlcipher3.Row
hex_key = pw.encode().hex()
db.execute(f'PRAGMA key="x\'{hex_key}\'"')

# ============================================================
# STATE POLICE / HIGHWAY PATROL (50 states)
# ============================================================
STATE_POLICE = [
    ("Alabama Law Enforcement Agency (ALEA)", "+1 (334) 517-2800", "https://www.alea.gov", "State Police"),
    ("Alaska State Troopers", "+1 (907) 269-5511", "https://dps.alaska.gov/ast", "State Police"),
    ("Arizona Department of Public Safety (AZDPS)", "+1 (602) 223-2000", "https://www.azdps.gov", "State Police"),
    ("Arkansas State Police", "+1 (501) 618-8000", "https://dps.arkansas.gov/law-enforcement/arkansas-state-police", "State Police"),
    ("California Highway Patrol (CHP)", "+1 (916) 843-3300", "https://www.chp.ca.gov", "State Police"),
    ("Colorado State Patrol", "+1 (303) 239-4501", "https://csp.colorado.gov", "State Police"),
    ("Connecticut State Police", "+1 (860) 685-8190", "https://portal.ct.gov/despp", "State Police"),
    ("Delaware State Police", "+1 (302) 739-5901", "https://dsp.delaware.gov", "State Police"),
    ("Florida Highway Patrol", "+1 (850) 617-2000", "https://www.flhsmv.gov", "State Police"),
    ("Georgia State Patrol", "+1 (404) 624-7700", "https://dps.georgia.gov", "State Police"),
    ("Hawaii Sheriff Division (Dept. of Law Enforcement)", "+1 (808) 586-1352", "https://dle.hawaii.gov", "State Police"),
    ("Idaho State Police", "+1 (208) 884-7000", "https://isp.idaho.gov", "State Police"),
    ("Illinois State Police", "+1 (217) 782-7263", "https://isp.illinois.gov", "State Police"),
    ("Indiana State Police", "+1 (317) 232-8248", "https://in.gov/isp", "State Police"),
    ("Iowa State Patrol", "+1 (515) 725-6095", "https://dps.iowa.gov", "State Police"),
    ("Kansas Highway Patrol", "+1 (785) 296-6800", "https://kansashighwaypatrol.gov", "State Police"),
    ("Kentucky State Police", "+1 (502) 782-1800", "https://kentuckystatepolice.ky.gov", "State Police"),
    ("Louisiana State Police", "+1 (225) 925-6325", "https://lsp.org", "State Police"),
    ("Maine State Police", "+1 (207) 624-7000", "https://www.maine.gov/dps/msp", "State Police"),
    ("Maryland State Police", "+1 (410) 653-4200", "https://mdsp.maryland.gov", "State Police"),
    ("Massachusetts State Police", "+1 (508) 820-2121", "https://www.mass.gov/msp", "State Police"),
    ("Michigan State Police", "+1 (517) 241-8000", "https://www.michigan.gov/msp", "State Police"),
    ("Minnesota State Patrol", "+1 (651) 201-7100", "https://dps.mn.gov/divisions/msp", "State Police"),
    ("Mississippi Highway Patrol", "+1 (601) 987-1212", "https://www.dps.ms.gov", "State Police"),
    ("Missouri State Highway Patrol", "+1 (573) 751-3313", "https://statepatrol.dps.mo.gov", "State Police"),
    ("Montana Highway Patrol", "+1 (406) 444-3780", "https://dojmt.gov/highwaypatrol", "State Police"),
    ("Nebraska State Patrol", "+1 (402) 471-4545", "https://statepatrol.nebraska.gov", "State Police"),
    ("Nevada State Police", "+1 (775) 684-4808", "https://nsi.nv.gov", "State Police"),
    ("New Hampshire State Police", "+1 (603) 223-4381", "https://www.nh.gov/safety/divisions/nhsp", "State Police"),
    ("New Jersey State Police", "+1 (609) 882-2000", "https://njsp.org", "State Police"),
    ("New Mexico State Police", "+1 (505) 841-9256", "https://www.dps.nm.gov", "State Police"),
    ("New York State Police", "+1 (518) 457-6721", "https://troopers.ny.gov", "State Police"),
    ("North Carolina State Highway Patrol", "+1 (919) 733-7952", "https://www.ncdps.gov/shp", "State Police"),
    ("North Dakota Highway Patrol", "+1 (701) 328-2455", "https://nd.gov/ndhp", "State Police"),
    ("Ohio State Highway Patrol", "+1 (614) 466-2660", "https://statepatrol.ohio.gov", "State Police"),
    ("Oklahoma Highway Patrol", "+1 (405) 425-2424", "https://dps.ok.gov", "State Police"),
    ("Oregon State Police", "+1 (503) 378-3720", "https://oregon.gov/osp", "State Police"),
    ("Pennsylvania State Police", "+1 (717) 783-5599", "https://www.psp.pa.gov", "State Police"),
    ("Rhode Island State Police", "+1 (401) 444-1000", "https://risp.ri.gov", "State Police"),
    ("South Carolina Highway Patrol", "+1 (803) 896-7920", "https://scdps.sc.gov", "State Police"),
    ("South Dakota Highway Patrol", "+1 (605) 773-3105", "https://dps.sd.gov/highway-patrol", "State Police"),
    ("Tennessee Highway Patrol", "+1 (615) 251-5166", "https://www.tn.gov/safety", "State Police"),
    ("Texas Highway Patrol (DPS)", "+1 (512) 424-2000", "https://www.dps.texas.gov", "State Police"),
    ("Utah Highway Patrol", "+1 (801) 965-4461", "https://highwaypatrol.utah.gov", "State Police"),
    ("Vermont State Police", "+1 (802) 244-8781", "https://vsp.vermont.gov", "State Police"),
    ("Virginia State Police", "+1 (804) 674-2000", "https://vsp.virginia.gov", "State Police"),
    ("Washington State Patrol", "+1 (360) 596-4000", "https://wsp.wa.gov", "State Police"),
    ("West Virginia State Police", "+1 (304) 746-2100", "https://wvsp.gov", "State Police"),
    ("Wisconsin State Patrol", "+1 (608) 266-3212", "https://wisconsindot.gov", "State Police"),
    ("Wyoming Highway Patrol", "+1 (307) 777-4301", "https://whp.wyo.gov", "State Police"),
]

# ============================================================
# FBI FIELD OFFICES (56)
# ============================================================
FBI_OFFICES = [
    ("FBI - Albany Field Office", "+1 (518) 465-7551", "https://albany.fbi.gov", "Law Enforcement"),
    ("FBI - Albuquerque Field Office", "+1 (505) 889-1300", "https://albuquerque.fbi.gov", "Law Enforcement"),
    ("FBI - Anchorage Field Office", "+1 (907) 276-4441", "https://anchorage.fbi.gov", "Law Enforcement"),
    ("FBI - Atlanta Field Office", "+1 (770) 216-3000", "https://atlanta.fbi.gov", "Law Enforcement"),
    ("FBI - Baltimore Field Office", "+1 (410) 265-8080", "https://baltimore.fbi.gov", "Law Enforcement"),
    ("FBI - Billings Field Office", "+1 (406) 248-8487", "https://billings.fbi.gov", "Law Enforcement"),
    ("FBI - Birmingham Field Office", "+1 (205) 326-6166", "https://birmingham.fbi.gov", "Law Enforcement"),
    ("FBI - Boston Field Office", "+1 (857) 386-2000", "https://boston.fbi.gov", "Law Enforcement"),
    ("FBI - Buffalo Field Office", "+1 (716) 856-7800", "https://buffalo.fbi.gov", "Law Enforcement"),
    ("FBI - Charlotte Field Office", "+1 (704) 672-6100", "https://charlotte.fbi.gov", "Law Enforcement"),
    ("FBI - Chicago Field Office", "+1 (312) 421-6700", "https://chicago.fbi.gov", "Law Enforcement"),
    ("FBI - Cincinnati Field Office", "+1 (513) 421-4310", "https://cincinnati.fbi.gov", "Law Enforcement"),
    ("FBI - Cleveland Field Office", "+1 (216) 522-1400", "https://cleveland.fbi.gov", "Law Enforcement"),
    ("FBI - Columbia Field Office", "+1 (803) 551-4200", "https://columbia.fbi.gov", "Law Enforcement"),
    ("FBI - Dallas Field Office", "+1 (972) 559-5000", "https://dallas.fbi.gov", "Law Enforcement"),
    ("FBI - Denver Field Office", "+1 (303) 629-7171", "https://denver.fbi.gov", "Law Enforcement"),
    ("FBI - Detroit Field Office", "+1 (313) 965-2323", "https://detroit.fbi.gov", "Law Enforcement"),
    ("FBI - El Paso Field Office", "+1 (915) 832-5000", "https://elpaso.fbi.gov", "Law Enforcement"),
    ("FBI - Honolulu Field Office", "+1 (808) 566-4300", "https://honolulu.fbi.gov", "Law Enforcement"),
    ("FBI - Houston Field Office", "+1 (713) 693-5000", "https://houston.fbi.gov", "Law Enforcement"),
    ("FBI - Indianapolis Field Office", "+1 (317) 595-4000", "https://indianapolis.fbi.gov", "Law Enforcement"),
    ("FBI - Jackson Field Office", "+1 (601) 948-5000", "https://jackson.fbi.gov", "Law Enforcement"),
    ("FBI - Jacksonville Field Office", "+1 (904) 248-7000", "https://jacksonville.fbi.gov", "Law Enforcement"),
    ("FBI - Kansas City Field Office", "+1 (816) 512-8200", "https://kansascity.fbi.gov", "Law Enforcement"),
    ("FBI - Las Vegas Field Office", "+1 (702) 385-1281", "https://lasvegas.fbi.gov", "Law Enforcement"),
    ("FBI - Little Rock Field Office", "+1 (501) 221-9100", "https://littlerock.fbi.gov", "Law Enforcement"),
    ("FBI - Los Angeles Field Office", "+1 (310) 477-6565", "https://losangeles.fbi.gov", "Law Enforcement"),
    ("FBI - Louisville Field Office", "+1 (502) 263-6000", "https://louisville.fbi.gov", "Law Enforcement"),
    ("FBI - Miami Field Office", "+1 (754) 703-2000", "https://miami.fbi.gov", "Law Enforcement"),
    ("FBI - Milwaukee Field Office", "+1 (414) 276-4684", "https://milwaukee.fbi.gov", "Law Enforcement"),
    ("FBI - Minneapolis Field Office", "+1 (763) 569-8000", "https://minneapolis.fbi.gov", "Law Enforcement"),
    ("FBI - Mobile Field Office", "+1 (251) 438-3674", "https://mobile.fbi.gov", "Law Enforcement"),
    ("FBI - Nashville Field Office", "+1 (615) 232-7500", "https://nashville.fbi.gov", "Law Enforcement"),
    ("FBI - New Haven Field Office", "+1 (203) 777-6311", "https://newhaven.fbi.gov", "Law Enforcement"),
    ("FBI - New Orleans Field Office", "+1 (504) 816-3000", "https://neworleans.fbi.gov", "Law Enforcement"),
    ("FBI - New York Field Office", "+1 (212) 384-1000", "https://newyork.fbi.gov", "Law Enforcement"),
    ("FBI - Newark Field Office", "+1 (973) 792-3000", "https://newark.fbi.gov", "Law Enforcement"),
    ("FBI - Norfolk Field Office", "+1 (757) 455-0100", "https://norfolk.fbi.gov", "Law Enforcement"),
    ("FBI - Oklahoma City Field Office", "+1 (405) 290-7770", "https://oklahomacity.fbi.gov", "Law Enforcement"),
    ("FBI - Omaha Field Office", "+1 (402) 493-8688", "https://omaha.fbi.gov", "Law Enforcement"),
    ("FBI - Philadelphia Field Office", "+1 (215) 418-4000", "https://philadelphia.fbi.gov", "Law Enforcement"),
    ("FBI - Phoenix Field Office", "+1 (623) 466-1999", "https://phoenix.fbi.gov", "Law Enforcement"),
    ("FBI - Pittsburgh Field Office", "+1 (412) 432-4000", "https://pittsburgh.fbi.gov", "Law Enforcement"),
    ("FBI - Portland Field Office", "+1 (503) 224-4181", "https://portland.fbi.gov", "Law Enforcement"),
    ("FBI - Richmond Field Office", "+1 (804) 261-1044", "https://richmond.fbi.gov", "Law Enforcement"),
    ("FBI - Sacramento Field Office", "+1 (916) 746-7000", "https://sacramento.fbi.gov", "Law Enforcement"),
    ("FBI - Salt Lake City Field Office", "+1 (801) 579-1400", "https://saltlakecity.fbi.gov", "Law Enforcement"),
    ("FBI - San Antonio Field Office", "+1 (210) 225-6741", "https://sanantonio.fbi.gov", "Law Enforcement"),
    ("FBI - San Diego Field Office", "+1 (858) 320-1800", "https://sandiego.fbi.gov", "Law Enforcement"),
    ("FBI - San Francisco Field Office", "+1 (415) 553-7400", "https://sanfrancisco.fbi.gov", "Law Enforcement"),
    ("FBI - San Juan Field Office", "+1 (787) 987-6500", "https://sanjuan.fbi.gov", "Law Enforcement"),
    ("FBI - Seattle Field Office", "+1 (206) 622-0460", "https://seattle.fbi.gov", "Law Enforcement"),
    ("FBI - Springfield Field Office", "+1 (217) 522-9675", "https://springfield.fbi.gov", "Law Enforcement"),
    ("FBI - St. Louis Field Office", "+1 (314) 589-2500", "https://stlouis.fbi.gov", "Law Enforcement"),
    ("FBI - Tampa Field Office", "+1 (813) 253-1000", "https://tampa.fbi.gov", "Law Enforcement"),
    ("FBI - Washington DC Field Office", "+1 (202) 278-2000", "https://washingtondc.fbi.gov", "Law Enforcement"),
]

# ============================================================
# DEA FIELD DIVISIONS
# ============================================================
DEA_DIVISIONS = [
    ("DEA - Atlanta Field Division", "+1 (404) 486-4700", "https://www.dea.gov/divisions/atlanta", "Law Enforcement"),
    ("DEA - Boston/New England Field Division", "+1 (617) 557-2100", "https://www.dea.gov/divisions/new-england", "Law Enforcement"),
    ("DEA - Chicago Field Division", "+1 (312) 353-7875", "https://www.dea.gov/divisions/chicago", "Law Enforcement"),
    ("DEA - Dallas Field Division", "+1 (214) 366-6900", "https://www.dea.gov/divisions/dallas", "Law Enforcement"),
    ("DEA - Denver Field Division", "+1 (303) 705-7300", "https://www.dea.gov/divisions/denver", "Law Enforcement"),
    ("DEA - Detroit Field Division", "+1 (313) 234-4000", "https://www.dea.gov/divisions/detroit", "Law Enforcement"),
    ("DEA - El Paso Field Division", "+1 (915) 832-6000", "https://www.dea.gov/divisions/el-paso", "Law Enforcement"),
    ("DEA - Houston Field Division", "+1 (713) 693-3000", "https://www.dea.gov/divisions/houston", "Law Enforcement"),
    ("DEA - Los Angeles Field Division", "+1 (213) 621-6700", "https://www.dea.gov/divisions/los-angeles", "Law Enforcement"),
    ("DEA - Miami Field Division", "+1 (571) 362-3364", "https://www.dea.gov/divisions/miami", "Law Enforcement"),
    ("DEA - New Orleans Field Division", "+1 (504) 840-1100", "https://www.dea.gov/divisions/new-orleans", "Law Enforcement"),
    ("DEA - New York Field Division", "+1 (212) 337-3900", "https://www.dea.gov/divisions/new-york", "Law Enforcement"),
    ("DEA - Philadelphia Field Division", "+1 (215) 625-2600", "https://www.dea.gov/divisions/philadelphia", "Law Enforcement"),
    ("DEA - Phoenix Field Division", "+1 (602) 664-5600", "https://www.dea.gov/divisions/phoenix", "Law Enforcement"),
    ("DEA - San Diego Field Division", "+1 (858) 616-4100", "https://www.dea.gov/divisions/san-diego", "Law Enforcement"),
    ("DEA - San Francisco Field Division", "+1 (415) 436-7800", "https://www.dea.gov/divisions/san-francisco", "Law Enforcement"),
    ("DEA - Seattle Field Division", "+1 (206) 553-5443", "https://www.dea.gov/divisions/seattle", "Law Enforcement"),
    ("DEA - St. Louis Field Division", "+1 (314) 539-2900", "https://www.dea.gov/divisions/st-louis", "Law Enforcement"),
    ("DEA - Washington DC Field Division", "+1 (202) 305-8500", "https://www.dea.gov/divisions/washington", "Law Enforcement"),
]

# ============================================================
# ATF FIELD DIVISIONS
# ============================================================
ATF_DIVISIONS = [
    ("ATF - Atlanta Field Division", "+1 (404) 417-2600", "https://www.atf.gov/field-divisions/atlanta", "Law Enforcement"),
    ("ATF - Baltimore Field Division", "+1 (410) 584-8100", "https://www.atf.gov/field-divisions/baltimore", "Law Enforcement"),
    ("ATF - Boston Field Division", "+1 (617) 557-1200", "https://www.atf.gov/field-divisions/boston", "Law Enforcement"),
    ("ATF - Charlotte Field Division", "+1 (704) 716-1800", "https://www.atf.gov/field-divisions/charlotte", "Law Enforcement"),
    ("ATF - Chicago Field Division", "+1 (312) 846-7200", "https://www.atf.gov/field-divisions/chicago", "Law Enforcement"),
    ("ATF - Columbus Field Division", "+1 (614) 827-8400", "https://www.atf.gov/field-divisions/columbus", "Law Enforcement"),
    ("ATF - Dallas Field Division", "+1 (972) 860-7100", "https://www.atf.gov/field-divisions/dallas", "Law Enforcement"),
    ("ATF - Denver Field Division", "+1 (303) 844-7200", "https://www.atf.gov/field-divisions/denver", "Law Enforcement"),
    ("ATF - Detroit Field Division", "+1 (313) 202-3000", "https://www.atf.gov/field-divisions/detroit", "Law Enforcement"),
    ("ATF - Houston Field Division", "+1 (281) 372-2400", "https://www.atf.gov/field-divisions/houston", "Law Enforcement"),
    ("ATF - Kansas City Field Division", "+1 (816) 559-0600", "https://www.atf.gov/field-divisions/kansas-city", "Law Enforcement"),
    ("ATF - Los Angeles Field Division", "+1 (818) 265-2500", "https://www.atf.gov/field-divisions/los-angeles", "Law Enforcement"),
    ("ATF - Miami Field Division", "+1 (954) 660-5200", "https://www.atf.gov/field-divisions/miami", "Law Enforcement"),
    ("ATF - Nashville Field Division", "+1 (615) 781-0500", "https://www.atf.gov/field-divisions/nashville", "Law Enforcement"),
    ("ATF - New Orleans Field Division", "+1 (504) 841-7000", "https://www.atf.gov/field-divisions/new-orleans", "Law Enforcement"),
    ("ATF - New York Field Division", "+1 (646) 335-2000", "https://www.atf.gov/field-divisions/new-york", "Law Enforcement"),
    ("ATF - Newark Field Division", "+1 (973) 776-4500", "https://www.atf.gov/field-divisions/newark", "Law Enforcement"),
    ("ATF - Philadelphia Field Division", "+1 (215) 446-7800", "https://www.atf.gov/field-divisions/philadelphia", "Law Enforcement"),
    ("ATF - Phoenix Field Division", "+1 (602) 776-6300", "https://www.atf.gov/field-divisions/phoenix", "Law Enforcement"),
    ("ATF - San Francisco Field Division", "+1 (510) 744-5400", "https://www.atf.gov/field-divisions/san-francisco", "Law Enforcement"),
    ("ATF - Seattle Field Division", "+1 (206) 553-7500", "https://www.atf.gov/field-divisions/seattle", "Law Enforcement"),
    ("ATF - St. Paul Field Division", "+1 (651) 726-2400", "https://www.atf.gov/field-divisions/st-paul", "Law Enforcement"),
    ("ATF - Tampa Field Division", "+1 (813) 216-3400", "https://www.atf.gov/field-divisions/tampa", "Law Enforcement"),
    ("ATF - Washington DC Field Division", "+1 (202) 648-8010", "https://www.atf.gov/field-divisions/washington", "Law Enforcement"),
]

# ============================================================
# US MARSHALS SERVICE DISTRICT OFFICES (key districts)
# ============================================================
USMS_OFFICES = [
    ("US Marshals - ND Alabama (Birmingham)", "+1 (205) 829-6611", "https://www.usmarshals.gov/local-districts/northern-district-of-alabama", "Law Enforcement"),
    ("US Marshals - MD Alabama (Montgomery)", "+1 (334) 223-7440", "https://www.usmarshals.gov/local-districts/middle-district-of-alabama", "Law Enforcement"),
    ("US Marshals - SD Alabama (Mobile)", "+1 (251) 690-2855", "https://www.usmarshals.gov/local-districts/southern-district-of-alabama", "Law Enforcement"),
    ("US Marshals - Alaska (Anchorage)", "+1 (907) 271-5154", "https://www.usmarshals.gov/local-districts/district-of-alaska", "Law Enforcement"),
    ("US Marshals - Arizona (Phoenix)", "+1 (602) 322-2800", "https://www.usmarshals.gov/local-districts/district-of-arizona", "Law Enforcement"),
    ("US Marshals - ED Arkansas (Little Rock)", "+1 (501) 604-5360", "https://www.usmarshals.gov/local-districts/eastern-district-of-arkansas", "Law Enforcement"),
    ("US Marshals - CD California (Los Angeles)", "+1 (213) 620-7676", "https://www.usmarshals.gov/local-districts/central-district-of-california", "Law Enforcement"),
    ("US Marshals - ND California (San Francisco)", "+1 (415) 436-7676", "https://www.usmarshals.gov/local-districts/northern-district-of-california", "Law Enforcement"),
    ("US Marshals - ED California (Sacramento)", "+1 (916) 930-2020", "https://www.usmarshals.gov/local-districts/eastern-district-of-california", "Law Enforcement"),
    ("US Marshals - SD California (San Diego)", "+1 (619) 557-6667", "https://www.usmarshals.gov/local-districts/southern-district-of-california", "Law Enforcement"),
    ("US Marshals - Colorado (Denver)", "+1 (303) 335-3800", "https://www.usmarshals.gov/local-districts/district-of-colorado", "Law Enforcement"),
    ("US Marshals - Connecticut (New Haven)", "+1 (203) 773-2108", "https://www.usmarshals.gov/local-districts/district-of-connecticut", "Law Enforcement"),
    ("US Marshals - DC (Washington)", "+1 (202) 803-8500", "https://www.usmarshals.gov/local-districts/district-of-columbia", "Law Enforcement"),
    ("US Marshals - Florida (Miami/SDFL)", "+1 (305) 591-4900", "https://www.usmarshals.gov/local-districts/southern-district-of-florida", "Law Enforcement"),
    ("US Marshals - Florida (Tampa/MDFL)", "+1 (813) 274-5890", "https://www.usmarshals.gov/local-districts/middle-district-of-florida", "Law Enforcement"),
    ("US Marshals - Florida (Jacksonville/NDFL)", "+1 (904) 360-4200", "https://www.usmarshals.gov/local-districts/northern-district-of-florida", "Law Enforcement"),
    ("US Marshals - Georgia (Atlanta/NDGA)", "+1 (404) 215-1300", "https://www.usmarshals.gov/local-districts/northern-district-of-georgia", "Law Enforcement"),
    ("US Marshals - Georgia (MDGA - Macon)", "+1 (478) 330-0200", "https://www.usmarshals.gov/local-districts/middle-district-of-georgia", "Law Enforcement"),
    ("US Marshals - Georgia (SDGA - Savannah)", "+1 (912) 652-4521", "https://www.usmarshals.gov/local-districts/southern-district-of-georgia", "Law Enforcement"),
    ("US Marshals - Illinois (Chicago/NDIL)", "+1 (312) 353-0450", "https://www.usmarshals.gov/local-districts/northern-district-of-illinois", "Law Enforcement"),
    ("US Marshals - Illinois (Springfield/CDIL)", "+1 (217) 492-4050", "https://www.usmarshals.gov/local-districts/central-district-of-illinois", "Law Enforcement"),
    ("US Marshals - Illinois (East St. Louis/SDIL)", "+1 (618) 482-9360", "https://www.usmarshals.gov/local-districts/southern-district-of-illinois", "Law Enforcement"),
    ("US Marshals - Massachusetts (Boston)", "+1 (617) 748-9100", "https://www.usmarshals.gov/local-districts/district-of-massachusetts", "Law Enforcement"),
    ("US Marshals - Michigan (Detroit/EDMI)", "+1 (313) 226-7900", "https://www.usmarshals.gov/local-districts/eastern-district-of-michigan", "Law Enforcement"),
    ("US Marshals - Michigan (Grand Rapids/WDMI)", "+1 (616) 456-2260", "https://www.usmarshals.gov/local-districts/western-district-of-michigan", "Law Enforcement"),
    ("US Marshals - Minnesota (Minneapolis)", "+1 (651) 848-1880", "https://www.usmarshals.gov/local-districts/district-of-minnesota", "Law Enforcement"),
    ("US Marshals - Missouri (St. Louis/EDMO)", "+1 (314) 539-2200", "https://www.usmarshals.gov/local-districts/eastern-district-of-missouri", "Law Enforcement"),
    ("US Marshals - Missouri (Kansas City/WDMO)", "+1 (816) 512-1300", "https://www.usmarshals.gov/local-districts/western-district-of-missouri", "Law Enforcement"),
    ("US Marshals - Nevada (Las Vegas)", "+1 (702) 388-6400", "https://www.usmarshals.gov/local-districts/district-of-nevada", "Law Enforcement"),
    ("US Marshals - New Jersey (Newark)", "+1 (973) 645-2410", "https://www.usmarshals.gov/local-districts/district-of-new-jersey", "Law Enforcement"),
    ("US Marshals - New York (Manhattan/SDNY)", "+1 (212) 637-2200", "https://www.usmarshals.gov/local-districts/southern-district-of-new-york", "Law Enforcement"),
    ("US Marshals - New York (Brooklyn/EDNY)", "+1 (718) 254-6300", "https://www.usmarshals.gov/local-districts/eastern-district-of-new-york", "Law Enforcement"),
    ("US Marshals - New York (Buffalo/WDNY)", "+1 (716) 843-5870", "https://www.usmarshals.gov/local-districts/western-district-of-new-york", "Law Enforcement"),
    ("US Marshals - New York (Albany/NDNY)", "+1 (518) 431-0130", "https://www.usmarshals.gov/local-districts/northern-district-of-new-york", "Law Enforcement"),
    ("US Marshals - North Carolina (Charlotte/WDNC)", "+1 (704) 344-6300", "https://www.usmarshals.gov/local-districts/western-district-of-north-carolina", "Law Enforcement"),
    ("US Marshals - North Carolina (Raleigh/EDNC)", "+1 (919) 856-4385", "https://www.usmarshals.gov/local-districts/eastern-district-of-north-carolina", "Law Enforcement"),
    ("US Marshals - North Carolina (Greensboro/MDNC)", "+1 (336) 332-4370", "https://www.usmarshals.gov/local-districts/middle-district-of-north-carolina", "Law Enforcement"),
    ("US Marshals - Ohio (Cleveland/NDOH)", "+1 (216) 522-2150", "https://www.usmarshals.gov/local-districts/northern-district-of-ohio", "Law Enforcement"),
    ("US Marshals - Ohio (Columbus/SDOH)", "+1 (614) 469-5850", "https://www.usmarshals.gov/local-districts/southern-district-of-ohio", "Law Enforcement"),
    ("US Marshals - Pennsylvania (Philadelphia/EDPA)", "+1 (215) 597-7430", "https://www.usmarshals.gov/local-districts/eastern-district-of-pennsylvania", "Law Enforcement"),
    ("US Marshals - Pennsylvania (Pittsburgh/WDPA)", "+1 (412) 894-3400", "https://www.usmarshals.gov/local-districts/western-district-of-pennsylvania", "Law Enforcement"),
    ("US Marshals - Pennsylvania (Scranton/MDPA)", "+1 (570) 346-5780", "https://www.usmarshals.gov/local-districts/middle-district-of-pennsylvania", "Law Enforcement"),
    ("US Marshals - Texas (Dallas/NDTX)", "+1 (214) 767-0836", "https://www.usmarshals.gov/local-districts/northern-district-of-texas", "Law Enforcement"),
    ("US Marshals - Texas (Houston/SDTX)", "+1 (713) 718-4800", "https://www.usmarshals.gov/local-districts/southern-district-of-texas", "Law Enforcement"),
    ("US Marshals - Texas (San Antonio/WDTX)", "+1 (210) 472-6540", "https://www.usmarshals.gov/local-districts/western-district-of-texas", "Law Enforcement"),
    ("US Marshals - Texas (Tyler/EDTX)", "+1 (903) 590-1300", "https://www.usmarshals.gov/local-districts/eastern-district-of-texas", "Law Enforcement"),
    ("US Marshals - Virginia (Alexandria/EDVA)", "+1 (703) 600-5100", "https://www.usmarshals.gov/local-districts/eastern-district-of-virginia", "Law Enforcement"),
    ("US Marshals - Virginia (Roanoke/WDVA)", "+1 (540) 857-5170", "https://www.usmarshals.gov/local-districts/western-district-of-virginia", "Law Enforcement"),
    ("US Marshals - Washington (Seattle/WDWA)", "+1 (206) 553-7970", "https://www.usmarshals.gov/local-districts/western-district-of-washington", "Law Enforcement"),
    ("US Marshals - Washington (Spokane/EDWA)", "+1 (509) 353-2260", "https://www.usmarshals.gov/local-districts/eastern-district-of-washington", "Law Enforcement"),
    ("US Marshals - Wisconsin (Milwaukee/EDWI)", "+1 (414) 297-3221", "https://www.usmarshals.gov/local-districts/eastern-district-of-wisconsin", "Law Enforcement"),
    ("US Marshals - Wisconsin (Madison/WDWI)", "+1 (608) 264-5168", "https://www.usmarshals.gov/local-districts/western-district-of-wisconsin", "Law Enforcement"),
]

# ============================================================
# INSERT ALL CONTACTS (skip duplicates by company name)
# ============================================================
def insert_contacts(contacts, vertical_name, notes_suffix=""):
    inserted = 0
    skipped = 0
    for company, phone, website, contact_type in contacts:
        existing = db.execute(
            "SELECT id FROM leads WHERE company = ?", (company,)
        ).fetchone()
        if existing:
            skipped += 1
            continue
        
        notes = f"HQ: {company}. Official website: {website}. Phone: {phone}."
        if notes_suffix:
            notes += " " + notes_suffix
        
        db.execute(
            "INSERT INTO leads (company, type, vertical, phone, website, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (company, contact_type, vertical_name, phone, website, notes, "us-expansion")
        )
        inserted += 1
    return inserted, skipped

# --- State Police ---
ins, skp = insert_contacts(STATE_POLICE, "USA",
    "Emergency: 911. State-level law enforcement agency. Social: varies by state.")
print(f"State Police: {ins} inserted, {skp} skipped")

# --- FBI Field Offices ---
ins, skp = insert_contacts(FBI_OFFICES, "USA",
    "Emergency: 911. FBI Tips: 1-800-CALL-FBI (1-800-225-5328) or tips.fbi.gov. Social: @FBI on X/Twitter.")
print(f"FBI Field Offices: {ins} inserted, {skp} skipped")

# --- DEA Field Divisions ---
ins, skp = insert_contacts(DEA_DIVISIONS, "USA",
    "DEA Tips: 1-877-792-2873. Social: @DEAHQ on X/Twitter.")
print(f"DEA Field Divisions: {ins} inserted, {skp} skipped")

# --- ATF Field Divisions ---
ins, skp = insert_contacts(ATF_DIVISIONS, "USA",
    "ATF Tips: 1-888-ATF-TIPS (1-888-283-8477). Social: @ATFHQ on X/Twitter.")
print(f"ATF Field Divisions: {ins} inserted, {skp} skipped")

# --- US Marshals District Offices ---
ins, skp = insert_contacts(USMS_OFFICES, "USA",
    "USMS Tips: 1-877-926-8332. Social: @USMarshalsHQ on X/Twitter.")
print(f"US Marshals Offices: {ins} inserted, {skp} skipped")

db.commit()

# Final summary
total_new = db.execute("SELECT COUNT(*) FROM leads WHERE source = 'us-expansion'").fetchone()[0]
total_us = db.execute("SELECT COUNT(*) FROM leads WHERE vertical = 'USA'").fetchone()[0]
print(f"\nTotal new US contacts added: {total_new}")
print(f"Total US contacts now: {total_us}")

# Show some samples
print("\n=== SAMPLE (first 5 state police) ===")
for r in db.execute("SELECT company, phone, website FROM leads WHERE source = 'us-expansion' AND type = 'State Police' ORDER BY company LIMIT 5").fetchall():
    print(f"  {r['company']}")
    print(f"    Phone: {r['phone']}  Web: {r['website']}")

print("\n=== SAMPLE (first 5 FBI offices) ===")
for r in db.execute("SELECT company, phone, website FROM leads WHERE source = 'us-expansion' AND company LIKE '%FBI%' ORDER BY company LIMIT 5").fetchall():
    print(f"  {r['company']}")
    print(f"    Phone: {r['phone']}  Web: {r['website']}")

db.close()
