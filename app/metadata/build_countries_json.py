"""Generate standard ISO 3166-1 countries dataset (249 countries and territories).

Includes:
- Country name in Vietnamese & English
- ISO 3166-1 alpha-2 code
- ITU-T country dial code (+...)
- Native / official name
- Flag emoji
- ISO 4217 Currency code
"""
import json
from pathlib import Path
import pycountry

OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "iso_countries.json"

# Vietnamese translation map for major and common countries
VI_NAMES = {
    "VN": "Việt Nam",
    "US": "Hoa Kỳ (Mỹ)",
    "GB": "Vương Quốc Anh",
    "FR": "Pháp",
    "DE": "Đức",
    "JP": "Nhật Bản",
    "KR": "Hàn Quốc",
    "KP": "Triều Tiên",
    "CN": "Trung Quốc",
    "RU": "Nga",
    "CA": "Canada",
    "AU": "Úc (Australia)",
    "SG": "Singapore",
    "TH": "Thái Lan",
    "MY": "Malaysia",
    "ID": "Indonesia",
    "PH": "Philippines",
    "LA": "Lào",
    "KH": "Campuchia",
    "MM": "Myanmar",
    "IN": "Ấn Độ",
    "TW": "Đài Loan",
    "HK": "Hồng Kông",
    "MO": "Ma Cao",
    "IT": "Ý (Italy)",
    "ES": "Tây Ban Nha",
    "PT": "Bồ Đào Nha",
    "NL": "Hà Lan",
    "BE": "Bỉ",
    "CH": "Thụy Sĩ",
    "SE": "Thụy Điển",
    "NO": "Na Uy",
    "DK": "Đan Mạch",
    "FI": "Phần Lan",
    "PL": "Ba Lan",
    "CZ": "Cộng Hòa Séc",
    "AT": "Áo (Austria)",
    "GR": "Hy Lạp",
    "TR": "Thổ Nhĩ Kỳ",
    "UA": "Ukraine",
    "BR": "Brazil",
    "AR": "Argentina",
    "MX": "Mexico",
    "CL": "Chile",
    "CO": "Colombia",
    "EG": "Ai Cập",
    "ZA": "Nam Phi",
    "NG": "Nigeria",
    "SA": "Ả Rập Xê Út",
    "AE": "UAE (Các TVQ Ả Rập Thống Nhất)",
    "IL": "Israel",
    "NZ": "New Zealand",
    "IE": "Ireland",
    "HU": "Hungary",
    "RO": "Romania",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "RS": "Serbia",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "IS": "Iceland",
    "LU": "Luxembourg",
    "MC": "Monaco",
    "QA": "Qatar",
    "KW": "Kuwait",
    "BH": "Bahrain",
    "OM": "Oman",
    "IQ": "Iraq",
    "IR": "Iran",
    "PK": "Pakistan",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "NP": "Nepal",
    "MN": "Mông Cổ",
    "BN": "Brunei",
    "TL": "Đông Timor",
    "PE": "Peru",
    "VE": "Venezuela",
    "UY": "Uruguay",
    "PY": "Paraguay",
    "BO": "Bolivia",
    "EC": "Ecuador",
    "CU": "Cuba",
    "JM": "Jamaica",
    "PA": "Panama",
    "CR": "Costa Rica",
    "MA": "Morocco",
    "DZ": "Algeria",
    "TN": "Tunisia",
    "KE": "Kenya",
    "ET": "Ethiopia",
    "GH": "Ghana",
    "TZ": "Tanzania",
    "UG": "Uganda",
    "VA": "Vatican",
}

# Standard dial codes for alpha-2
DIAL_CODES = {
    "AF": "+93", "AL": "+355", "DZ": "+213", "AS": "+1-684", "AD": "+376",
    "AO": "+244", "AI": "+1-264", "AQ": "+672", "AG": "+1-268", "AR": "+54",
    "AM": "+374", "AW": "+297", "AU": "+61", "AT": "+43", "AZ": "+994",
    "BS": "+1-242", "BH": "+973", "BD": "+880", "BB": "+1-246", "BY": "+375",
    "BE": "+32", "BZ": "+501", "BJ": "+229", "BM": "+1-441", "BT": "+975",
    "BO": "+591", "BA": "+387", "BW": "+267", "BV": "+47", "BR": "+55",
    "IO": "+246", "BN": "+673", "BG": "+359", "BF": "+226", "BI": "+257",
    "KH": "+855", "CM": "+237", "CA": "+1", "CV": "+238", "KY": "+1-345",
    "CF": "+236", "TD": "+235", "CL": "+56", "CN": "+86", "CX": "+61",
    "CC": "+61", "CO": "+57", "KM": "+269", "CG": "+242", "CD": "+243",
    "CK": "+682", "CR": "+506", "CI": "+225", "HR": "+385", "CU": "+53",
    "CY": "+357", "CZ": "+420", "DK": "+45", "DJ": "+253", "DM": "+1-767",
    "DO": "+1-809", "EC": "+593", "EG": "+20", "SV": "+503", "GQ": "+240",
    "ER": "+291", "EE": "+372", "ET": "+251", "FK": "+500", "FO": "+298",
    "FJ": "+679", "FI": "+358", "FR": "+33", "GF": "+594", "PF": "+689",
    "TF": "+262", "GA": "+241", "GM": "+220", "GE": "+995", "DE": "+49",
    "GH": "+233", "GI": "+350", "GR": "+30", "GL": "+299", "GD": "+1-473",
    "GP": "+590", "GU": "+1-671", "GT": "+502", "GG": "+44-1481", "GN": "+224",
    "GW": "+245", "GY": "+592", "HT": "+509", "HM": "+672", "VA": "+379",
    "HN": "+504", "HK": "+852", "HU": "+36", "IS": "+354", "IN": "+91",
    "ID": "+62", "IR": "+98", "IQ": "+964", "IE": "+353", "IM": "+44-1624",
    "IL": "+972", "IT": "+39", "JM": "+1-876", "JP": "+81", "JE": "+44-1534",
    "JO": "+962", "KZ": "+7", "KE": "+254", "KI": "+686", "KP": "+850",
    "KR": "+82", "KW": "+965", "KG": "+996", "LA": "+856", "LV": "+371",
    "LB": "+961", "LS": "+266", "LR": "+231", "LY": "+218", "LI": "+423",
    "LT": "+370", "LU": "+352", "MO": "+853", "MK": "+389", "MG": "+261",
    "MW": "+265", "MY": "+60", "MV": "+960", "ML": "+223", "MT": "+356",
    "MH": "+692", "MQ": "+596", "MR": "+222", "MU": "+230", "YT": "+262",
    "MX": "+52", "FM": "+691", "MD": "+373", "MC": "+377", "MN": "+976",
    "ME": "+382", "MS": "+1-664", "MA": "+212", "MZ": "+258", "MM": "+95",
    "NA": "+264", "NR": "+674", "NP": "+977", "NL": "+31", "NC": "+687",
    "NZ": "+64", "NI": "+505", "NE": "+227", "NG": "+234", "NU": "+683",
    "NF": "+672", "MP": "+1-670", "NO": "+47", "OM": "+968", "PK": "+92",
    "PW": "+680", "PS": "+970", "PA": "+507", "PG": "+675", "PY": "+595",
    "PE": "+51", "PH": "+63", "PN": "+64", "PL": "+48", "PT": "+351",
    "PR": "+1-787", "QA": "+974", "RE": "+262", "RO": "+40", "RU": "+7",
    "RW": "+250", "BL": "+590", "SH": "+290", "KN": "+1-869", "LC": "+1-758",
    "MF": "+590", "PM": "+508", "VC": "+1-784", "WS": "+685", "SM": "+378",
    "ST": "+239", "SA": "+966", "SN": "+221", "RS": "+381", "SC": "+248",
    "SL": "+232", "SG": "+65", "SX": "+1-721", "SK": "+421", "SI": "+386",
    "SB": "+677", "SO": "+252", "ZA": "+27", "GS": "+500", "SS": "+211",
    "ES": "+34", "LK": "+94", "SD": "+249", "SR": "+597", "SJ": "+47",
    "SZ": "+268", "SE": "+46", "CH": "+41", "SY": "+963", "TW": "+886",
    "TJ": "+992", "TZ": "+255", "TH": "+66", "TL": "+670", "TG": "+228",
    "TK": "+690", "TO": "+676", "TT": "+1-868", "TN": "+216", "TR": "+90",
    "TM": "+993", "TC": "+1-649", "TV": "+688", "UG": "+256", "UA": "+380",
    "AE": "+971", "GB": "+44", "US": "+1", "UM": "+1", "UY": "+598",
    "UZ": "+998", "VU": "+678", "VE": "+58", "VN": "+84", "VG": "+1-284",
    "VI": "+1-340", "WF": "+681", "EH": "+212", "YE": "+967", "ZM": "+260",
    "ZW": "+263", "AX": "+358-18", "BQ": "+599", "CW": "+599"
}

# Currency mapping
CURRENCIES = {
    "VN": "VND", "US": "USD", "GB": "GBP", "FR": "EUR", "DE": "EUR",
    "JP": "JPY", "KR": "KRW", "KP": "KPW", "CN": "CNY", "RU": "RUB",
    "CA": "CAD", "AU": "AUD", "SG": "SGD", "TH": "THB", "MY": "MYR",
    "ID": "IDR", "PH": "PHP", "LA": "LAK", "KH": "KHR", "MM": "MMK",
    "IN": "INR", "TW": "TWD", "HK": "HKD", "MO": "MOP", "IT": "EUR",
    "ES": "EUR", "PT": "EUR", "NL": "EUR", "BE": "EUR", "CH": "CHF",
    "SE": "SEK", "NO": "NOK", "DK": "DKK", "FI": "EUR", "PL": "PLN",
    "CZ": "CZK", "AT": "EUR", "GR": "EUR", "TR": "TRY", "UA": "UAH",
    "BR": "BRL", "AR": "ARS", "MX": "MXN", "CL": "CLP", "CO": "COP",
    "EG": "EGP", "ZA": "ZAR", "NG": "NGN", "SA": "SAR", "AE": "AED",
    "IL": "ILS", "NZ": "NZD", "IE": "EUR", "HU": "HUF", "RO": "RON",
    "BG": "BGN", "HR": "EUR", "RS": "RSD", "SK": "EUR", "SI": "EUR",
    "IS": "ISK", "LU": "EUR", "MC": "EUR", "QA": "QAR", "KW": "KWD",
    "BH": "BHD", "OM": "OMR", "IQ": "IQD", "IR": "IRR", "PK": "PKR",
    "BD": "BDT", "LK": "LKR", "NP": "NPR", "MN": "MNT", "BN": "BND",
    "TL": "USD", "PE": "PEN", "VE": "VES", "UY": "UYU", "PY": "PYG",
    "BO": "BOB", "EC": "USD", "CU": "CUP", "JM": "JMD", "PA": "PAB",
    "CR": "CRC", "MA": "MAD", "DZ": "DZD", "TN": "TND", "KE": "KES",
    "ET": "ETB", "GH": "GHS", "TZ": "TZS", "UG": "UGX", "VA": "EUR"
}


def build():
    countries = list(pycountry.countries)
    # Sort alphabetically by country name
    countries.sort(key=lambda c: c.name)

    items = []
    for idx, c in enumerate(countries, start=1):
        code = c.alpha_2
        # Flag emoji
        flag = getattr(c, "flag", "".join(chr(127397 + ord(char)) for char in code))
        # Name
        name = VI_NAMES.get(code, c.name)
        # Native or English official name
        native_name = getattr(c, "official_name", c.name)
        # Dial code
        dial = DIAL_CODES.get(code, "+0")
        # Currency
        currency = CURRENCIES.get(code, "USD")

        items.append({
            "country_code": code,
            "name": name,
            "phone_code": dial,
            "native_name": native_name,
            "flag_emoji": flag,
            "currency_code": currency,
            "status": "active",
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"Successfully generated {len(items)} countries into {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
