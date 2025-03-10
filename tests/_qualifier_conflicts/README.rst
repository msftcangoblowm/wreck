qualifier conflicts
====================

qualifier_0.unlock::

    tomli
    typing-extensions<4.12.2
    colorama;os_name == "nt"
    dolorama;os_name == "nt"

qualifier_1.unlock::

    tomli>=2.0.2; python_version<"3.11"
    typing-extensions; python_version<"3.10"
    colorama>=0.4.5 ;platform_system=="Windows"
    dolorama>=0.4.6 ;platform_system=="Windows"

qualifier_0.lock::

    # a previous tagged release version **and** missing qualifier, `; python_version < "3.11"`
    # missing qualifier(s) --> warning message. Not the priority; don't fix
    # Solution: temporary nudge pin `tomli>=2.0.2` or just sync to latest
    tomli==2.0.1

    # constraints-various.lock chose 4.12.2 constraints-conflicts.unlock `typing-extensions<4.12.2`
    # missing qualifier(s) --> warning message. Not the priority; don't fix
    # Solution: sync chose constrained (previous tagged release) 4.12.1
    typing-extensions==4.12.1

    # missing qualifier; both qualifiers are equivalents. Which qualifier gets used?!
    colorama==0.4.6
    # if same versions and missing or varying qualifiers **is not fixed**!
    dolorama==0.4.6

qualifier_1.lock::

    tomli==2.0.2 ; python_version < "3.11"
        # via -r constraints-various.unlock
    typing-extensions==4.12.2 ; python_version < "3.10"
        # via -r constraints-various.unlock
    # missing qualifier; both qualifiers are equivalents. Which qualifier gets used?!
    colorama==0.4.5
    # if same versions and missing or varying qualifiers **is not fixed**!
    dolorama==0.4.6
