*** Settings ***
Library     RequestsLibrary
Library     Collections
Library     EleKeywords

Suite Setup     Setup Api Tests
Suite Teardown  Teardown Api Tests

*** Variables ***
${FLASK_URL}    http://127.0.0.1:5099

*** Test Cases ***
GET /api Returns HTTP 200
    ${response}=    GET    ${FLASK_URL}/api
    Should Be Equal As Integers    ${response.status_code}    200

Response Has All Required Keys
    ${response}=    GET    ${FLASK_URL}/api
    ${json}=    Set Variable    ${response.json()}
    FOR    ${key}    IN    current_time    current_price    green_led    yellow_led    red_led    power    avg_power    daily_cost
        Dictionary Should Contain Key    ${json}    ${key}
    END

Green LED When Spot Price Below Threshold
    Set Test Price    0.0
    ${response}=    GET    ${FLASK_URL}/api
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Integers    ${json}[green_led]    1
    Should Be Equal As Integers    ${json}[yellow_led]    0
    Should Be Equal As Integers    ${json}[red_led]    0

Yellow LED When Spot Price In Mid Range
    Set Test Price    5.0
    ${response}=    GET    ${FLASK_URL}/api
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Integers    ${json}[green_led]    0
    Should Be Equal As Integers    ${json}[yellow_led]    1
    Should Be Equal As Integers    ${json}[red_led]    0

Red LED When Spot Price Above High Threshold
    Set Test Price    10.0
    ${response}=    GET    ${FLASK_URL}/api
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Integers    ${json}[green_led]    0
    Should Be Equal As Integers    ${json}[yellow_led]    0
    Should Be Equal As Integers    ${json}[red_led]    1

Price Includes Markup And VAT
    Set Test Price    1.0
    ${response}=    GET    ${FLASK_URL}/api
    ${json}=    Set Variable    ${response.json()}
    ${expected}=    Calculate Expected Price    1.0
    ${diff}=    Evaluate    abs(${json}[current_price] - ${expected})
    Should Be True    ${diff} < 0.01

Empty Log Returns Valid Response Without Crash
    [Documentation]    Regression: was TypeError at latest_power_data[2] when log is empty
    Set Test Price    1.0
    ${empty}=    Create Header Only Log
    Set Log File    ${empty}
    ${response}=    GET    ${FLASK_URL}/api
    Should Be Equal As Integers    ${response.status_code}    200
    ${json}=    Set Variable    ${response.json()}
    Should Be Equal As Numbers    ${json}[power]    0
    Should Be Equal As Numbers    ${json}[avg_power]    0
    [Teardown]    Restore Default Log
