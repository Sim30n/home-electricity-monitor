*** Settings ***
Library     Collections
Library     EleKeywords

*** Test Cases ***
Get Latest Data Returns Correct Values
    ${path}=    Create Single Entry Log    1.2    1.5
    ${result}=    Read Latest Log Data    ${path}
    Should Not Be Equal    ${result}    ${None}
    ${today}=    Evaluate    __import__('datetime').date.today().strftime('%Y-%m-%d')
    Should Start With    ${result}[0]    ${today}
    Should Be Equal As Numbers    ${result}[1]    1.2
    Should Be Equal As Numbers    ${result}[2]    1.5
    [Teardown]    Cleanup Temp Files

Get Latest Data With Header Only Returns None
    ${path}=    Create Header Only Log
    ${result}=    Read Latest Log Data    ${path}
    Should Be Equal    ${result}    ${None}
    [Teardown]    Cleanup Temp Files

Get Latest Data With Missing File Returns None
    ${result}=    Read Latest Log Data    /nonexistent/path/no_such_file.log
    Should Be Equal    ${result}    ${None}

Get Today Data Filters By Current Date
    ${path}=    Create Mixed Date Log    1.2    1.3
    ${entries}=    Read Today Log Data    ${path}
    Length Should Be    ${entries}    2
    Should Be Equal As Numbers    ${entries}[0][power_kw]    1.2
    Should Be Equal As Numbers    ${entries}[1][power_kw]    1.3
    [Teardown]    Cleanup Temp Files

Get Today Data Skips Malformed Lines
    ${path}=    Create Malformed Log    1.2    1.4
    ${entries}=    Read Today Log Data    ${path}
    Length Should Be    ${entries}    2
    [Teardown]    Cleanup Temp Files

Get All Data Returns Full List Of Dicts
    ${path}=    Create Multi Entry Log    1.2    1.3
    ${data}=    Read All Log Data    ${path}
    Length Should Be    ${data}    2
    Should Be Equal As Integers    ${data}[0][ldr]    450
    Should Be Equal As Numbers    ${data}[0][power_kw]    1.2
    Should Be Equal As Numbers    ${data}[1][power_kw]    1.3
    [Teardown]    Cleanup Temp Files

Get All Data With Header Only Returns Empty List
    ${path}=    Create Header Only Log
    ${data}=    Read All Log Data    ${path}
    Length Should Be    ${data}    0
    [Teardown]    Cleanup Temp Files
