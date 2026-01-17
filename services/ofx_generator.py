import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class OFXGenerator:
    """Service class to generate OFX files"""
    
    def generate_ofx(self, securities_data, target_date, account_id='00000'):
        """Generate OFX content from securities data"""
        try:
            date_formatted = target_date.strftime('%Y%m%d000000[+9:JST]')
            date_simple = target_date.strftime('%Y%m%d')
            
            # Determine primary currency (JPY if any Japanese securities, otherwise USD)
            primary_currency = 'JPY'
            if all(sec.get('currency') == 'USD' for sec in securities_data):
                primary_currency = 'USD'
            
            # Start building OFX content
            ofx_content = self._get_ofx_header(date_formatted)
            
            # Add investment statement section
            ofx_content += self._get_investment_statement_start(date_formatted, primary_currency, account_id)
            
            # Add position list
            ofx_content += '<INVPOSLIST>\n'
            
            for security in securities_data:
                ofx_content += self._get_position_entry(security, date_formatted)
            
            ofx_content += '</INVPOSLIST>\n'
            ofx_content += self._get_investment_statement_end()
            
            # Add security list section
            ofx_content += self._get_security_list_start()
            ofx_content += '<SECLIST>\n'
            
            for security in securities_data:
                ofx_content += self._get_security_info(security)
            
            ofx_content += '</SECLIST>\n'
            ofx_content += self._get_security_list_end()
            
            # Close OFX
            ofx_content += '</OFX>\n'
            
            return ofx_content
        
        except Exception as e:
            logger.error(f"Error generating OFX: {str(e)}")
            raise
    
    def _get_ofx_header(self, date_formatted):
        """Generate OFX header"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<?OFX OFXHEADER="200" VERSION="200" SECURITY="NONE" OLDFILEUID="NONE" NEWFILEUID="NONE"?>
<!--
OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:UTF-8
CHARSET:UNICODE
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
-->
<OFX>
<SIGNONMSGSRSV1><SONRS><STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS><DTSERVER>{}</DTSERVER><LANGUAGE>JPN</LANGUAGE><FI><ORG>PURSE/0.9</ORG></FI></SONRS></SIGNONMSGSRSV1>
'''.format(date_formatted)
    
    def _get_investment_statement_start(self, date_formatted, currency, account_id='00000'):
        """Generate investment statement opening"""
        return '''<INVSTMTMSGSRSV1>
<INVSTMTTRNRS>
<TRNUID>0</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
<INVSTMTRS>
<DTASOF>{}</DTASOF>
<CURDEF>{}</CURDEF>
<INVACCTFROM><BROKERID>SecuOFX</BROKERID><ACCTID>{}</ACCTID></INVACCTFROM>
'''.format(date_formatted, currency, account_id)
    
    def _get_position_entry(self, security, date_formatted):
        """Generate position entry for a security"""
        security_type = security.get('type', 'US_STOCK')
        code = security.get('code', '')
        price_raw = security.get('price', '0')
        
        # Ensure price is properly formatted as number
        try:
            if isinstance(price_raw, str):
                price_value = float(price_raw.replace(',', ''))
            else:
                price_value = float(price_raw)
        except (ValueError, TypeError):
            price_value = 0.0
        
        # For Japanese mutual funds, divide by 10,000 (NAV is per 10,000 units)
        if security_type == 'JP_MUTUALFUND':
            price_value = price_value / 10000.0
        
        price = str(price_value)
        
        # Determine position type and unique ID type
        if security_type == 'JP_STOCK':
            pos_type = 'POSSTOCK'
            unique_id = code.replace('.T', '').replace('.O', '').replace('.N', '').replace('.F', '').replace('.S', '')
            unique_id_type = 'JP:SIC'
        elif security_type == 'JP_MUTUALFUND':
            pos_type = 'POSMF'
            unique_id = code
            unique_id_type = 'JP:ITAJ'
        else:  # US_STOCK
            pos_type = 'POSSTOCK'
            unique_id = code
            unique_id_type = 'NASDAQ'
        
        return '''<{}><INVPOS><SECID><UNIQUEID>{}</UNIQUEID><UNIQUEIDTYPE>{}</UNIQUEIDTYPE></SECID><HELDINACCT>CASH</HELDINACCT><POSTYPE>LONG</POSTYPE><UNITS>0</UNITS><UNITPRICE>{}</UNITPRICE><MKTVAL>0</MKTVAL><DTPRICEASOF>{}</DTPRICEASOF></INVPOS></{}>
'''.format(pos_type, unique_id, unique_id_type, price, date_formatted, pos_type)
    
    def _get_investment_statement_end(self):
        """Generate investment statement closing"""
        return '''<INVBAL><AVAILCASH>0</AVAILCASH><MARGINBALANCE>0</MARGINBALANCE><SHORTBALANCE>0</SHORTBALANCE></INVBAL>
</INVSTMTRS>
</INVSTMTTRNRS>
</INVSTMTMSGSRSV1>
'''
    
    def _get_security_list_start(self):
        """Generate security list opening"""
        return '''<SECLISTMSGSRSV1>
<SECLISTTRNRS>
<TRNUID>0</TRNUID>
<STATUS><CODE>0</CODE><SEVERITY>INFO</SEVERITY></STATUS>
</SECLISTTRNRS>
'''
    
    def _get_security_info(self, security):
        """Generate security information entry"""
        security_type = security.get('type', 'US_STOCK')
        code = security.get('code', '')
        name = security.get('name', code)
        
        # Determine security info type and unique ID
        if security_type == 'JP_STOCK':
            info_type = 'STOCKINFO'
            unique_id = code.replace('.T', '').replace('.O', '').replace('.N', '').replace('.F', '').replace('.S', '')
            unique_id_type = 'JP:SIC'
        elif security_type == 'JP_MUTUALFUND':
            info_type = 'MFINFO'
            unique_id = code
            unique_id_type = 'JP:ITAJ'
        else:  # US_STOCK
            info_type = 'STOCKINFO'
            unique_id = code
            unique_id_type = 'NASDAQ'
        
        # Escape XML special characters in name
        escaped_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        return '''<{}><SECINFO><SECID><UNIQUEID>{}</UNIQUEID><UNIQUEIDTYPE>{}</UNIQUEIDTYPE></SECID><SECNAME>{}</SECNAME></SECINFO></{}>
'''.format(info_type, unique_id, unique_id_type, escaped_name, info_type)
    
    def _get_security_list_end(self):
        """Generate security list closing"""
        return '''</SECLISTMSGSRSV1>
'''
