*** Settings ***
Library     Collections
Library     EleKeywords
Library     OperatingSystem

*** Variables ***
${XML_FIXTURE}    ${CURDIR}/test_data/price_response.xml

*** Test Cases ***
XML Parsing Returns Non Empty Dict
    ${xml}=    Get File    ${XML_FIXTURE}
    ${prices}=    Parse Price Xml    ${xml}
    Should Not Be Empty    ${prices}

All Dict Keys Are ISO8601 Timestamps With Timezone
    ${xml}=    Get File    ${XML_FIXTURE}
    ${prices}=    Parse Price Xml    ${xml}
    @{keys}=    Get Dictionary Keys    ${prices}
    FOR    ${k}    IN    @{keys}
        Should Match Regexp    ${k}    \\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[+-]\\d{2}:\\d{2}
    END

Price Conversion Divides EUR Per MWh By Ten
    [Documentation]    100 EUR/MWh → 10.0 c/kWh, 50 EUR/MWh → 5.0 c/kWh
    ${xml}=    Get File    ${XML_FIXTURE}
    ${prices}=    Parse Price Xml    ${xml}
    @{values}=    Get Dictionary Values    ${prices}
    Should Contain    ${values}    ${10.0}
    Should Contain    ${values}    ${5.0}

UTC Timestamps Are Converted To Helsinki Winter Time
    [Documentation]    Fixture starts at 2026-01-15T10:00Z which is 12:00+02:00 in Helsinki (winter)
    ${xml}=    Get File    ${XML_FIXTURE}
    ${prices}=    Parse Price Xml    ${xml}
    @{keys}=    Get Dictionary Keys    ${prices}
    ${first_key}=    Set Variable    ${keys}[0]
    Should Contain    ${first_key}    T12:00:00
    Should Contain    ${first_key}    +02:00

Both Points From XML Are Present
    ${xml}=    Get File    ${XML_FIXTURE}
    ${prices}=    Parse Price Xml    ${xml}
    Length Should Be    ${prices}    2
