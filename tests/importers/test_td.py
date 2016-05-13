"""Unit tests for beansoup.importers.td module."""

import datetime
from os import path

from beancount.ingest import cache
from beancount.parser import cmptest

from beansoup.importers import td
from beansoup.utils import testing


class TestTDImporter(cmptest.TestCase):

    @testing.docfile(mode='w', suffix='.csv')
    def test_importer_against_asset(self, filename):
        """
        04/01/2016,12-345 Smith    RLS,404.38,,5194.21
        04/05/2016,COSTCO #9876543,60.24,,5133.97
        04/05/2016,METRO ETS 2020,34.90,,5099.07
        04/05/2016,POISSONERIE DU,31.78,,5067.29
        04/05/2016,LES DOUCEURS DU,12.39,,5054.90
        04/05/2016,FROMAGERIE ATWA,42.17,,5012.73
        04/07/2016,CHQ#00123-456789,16.00,,4996.73
        04/12/2016,FROMAGERIE ATWA,39.46,,4957.27
        04/12/2016,DAVID'S TEA,27.50,,4929.77
        04/12/2016,PATISSERIE SAIN,32.00,,4897.77
        04/12/2016,GAZ METRO        BPY,247.26,,4650.51
        04/14/2016,VIDEOTRON LTEE   BPY,237.74,,4412.77
        04/14/2016,TD VISA      A1B2C3,74.37,,4338.40
        04/16/2016,FRUITERIE ATWAT,24.65,,4313.75
        04/16/2016,POISSONERIE NOU,64.79,,4248.96
        04/16/2016,CHQ#00125-9876543,160.00,,4088.96
        04/19/2016,CHQ#00124-9876543,900.00,,3188.96
        04/22/2016,AMEX         B2C3D4,734.59,,2454.37
        04/23/2016,POISSONERIE DU,57.18,,2397.19
        04/28/2016,BELL CANADA      BPY,25.30,,2371.89
        04/29/2016,CINEPLEX #9172,23.00,,2348.89
        04/29/2016,CANADA           RIT,,345.24,2694.13
        04/29/2016,12345678900WIRE,,210.32,2904.45
        04/30/2016,BARON SPORTS,21.28,,2883.17
        """
        file = cache.get_file(filename)

        account = 'Assets:TD:Checking'
        importer = td.Importer(account, 'CAD', 'td-checking',
                               first_day=1,
                               filename_regexp=path.basename(filename))

        assert importer.file_account(file) == account
        assert importer.file_name(file) == 'td-checking.csv'
        assert importer.identify(file)
        assert importer.file_date(file) == datetime.date(2016, 4, 30)

        entries = importer.extract(file)
        self.assertEqualEntries("""
        2016-04-01 * "12-345 Smith    RLS"
          Assets:TD:Checking  -404.38 CAD
        
        2016-04-05 * "COSTCO #9876543"
          Assets:TD:Checking  -60.24 CAD
        
        2016-04-05 * "METRO ETS 2020"
          Assets:TD:Checking  -34.90 CAD
        
        2016-04-05 * "POISSONERIE DU"
          Assets:TD:Checking  -31.78 CAD
        
        2016-04-05 * "LES DOUCEURS DU"
          Assets:TD:Checking  -12.39 CAD
        
        2016-04-05 * "FROMAGERIE ATWA"
          Assets:TD:Checking  -42.17 CAD
        
        2016-04-07 * "CHQ#00123-456789"
          Assets:TD:Checking  -16.00 CAD
        
        2016-04-12 * "FROMAGERIE ATWA"
          Assets:TD:Checking  -39.46 CAD
        
        2016-04-12 * "DAVID'S TEA"
          Assets:TD:Checking  -27.50 CAD
        
        2016-04-12 * "PATISSERIE SAIN"
          Assets:TD:Checking  -32.00 CAD
        
        2016-04-12 * "GAZ METRO        BPY"
          Assets:TD:Checking  -247.26 CAD
        
        2016-04-14 * "VIDEOTRON LTEE   BPY"
          Assets:TD:Checking  -237.74 CAD
        
        2016-04-14 * "TD VISA      A1B2C3"
          Assets:TD:Checking  -74.37 CAD
        
        2016-04-16 * "FRUITERIE ATWAT"
          Assets:TD:Checking  -24.65 CAD
        
        2016-04-16 * "POISSONERIE NOU"
          Assets:TD:Checking  -64.79 CAD
        
        2016-04-16 * "CHQ#00125-9876543"
          Assets:TD:Checking  -160.00 CAD
        
        2016-04-19 * "CHQ#00124-9876543"
          Assets:TD:Checking  -900.00 CAD
        
        2016-04-22 * "AMEX         B2C3D4"
          Assets:TD:Checking  -734.59 CAD
        
        2016-04-23 * "POISSONERIE DU"
          Assets:TD:Checking  -57.18 CAD
        
        2016-04-28 * "BELL CANADA      BPY"
          Assets:TD:Checking  -25.30 CAD
        
        2016-04-29 * "CINEPLEX #9172"
          Assets:TD:Checking  -23.00 CAD
        
        2016-04-29 * "CANADA           RIT"
          Assets:TD:Checking  345.24 CAD
        
        2016-04-29 * "12345678900WIRE"
          Assets:TD:Checking  210.32 CAD
        
        2016-04-30 * "BARON SPORTS"
          Assets:TD:Checking  -21.28 CAD
        
        2016-05-01 balance Assets:TD:Checking   2883.17 CAD
        """, entries)

    @testing.docfile(mode='w', suffix='.csv')
    def test_importer_against_liability(self, filename):
        """
        12/06/2015,SKYPE                    123456789,14.00,,97.62
        12/07/2015,STM-LAURIER              MONTREAL,22.50,,120.12
        12/13/2015,PAYMENT - THANK YOU,,97.62,22.50
        12/14/2015,RESTAURANT PHAYA THAI    MONTREAL,40.00,,62.50
        12/16/2015,STM-CHARLEVOIX           MONTREAL,45.00,,107.50
        """
        file = cache.get_file(filename)

        account = 'Liabilities:TD:Visa'
        importer = td.Importer(account, 'CAD', 'td-visa',
                               first_day=4,
                               filename_regexp=path.basename(filename))

        assert importer.file_account(file) == account
        assert importer.file_name(file) == 'td-visa.csv'
        assert importer.identify(file)
        assert importer.file_date(file) == datetime.date(2016, 1, 3)

        entries = importer.extract(file)
        self.assertEqualEntries("""
        2015-12-06 * "SKYPE                    123456789"
          Liabilities:TD:Visa  -14.00 CAD
        
        2015-12-07 * "STM-LAURIER              MONTREAL"
          Liabilities:TD:Visa  -22.50 CAD
        
        2015-12-13 * "PAYMENT - THANK YOU"
          Liabilities:TD:Visa  97.62 CAD
        
        2015-12-14 * "RESTAURANT PHAYA THAI    MONTREAL"
          Liabilities:TD:Visa  -40.00 CAD
        
        2015-12-16 * "STM-CHARLEVOIX           MONTREAL"
          Liabilities:TD:Visa  -45.00 CAD
        
        2016-01-04 balance Liabilities:TD:Visa    -107.50 CAD
        """, entries)
