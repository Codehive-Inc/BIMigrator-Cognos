We are working on a tool to migrate Tableau TWB files to Power BI TMDL files.
The logic must be fully customizable using templates and configuration files.

1. please use twb-to-pbi.yaml for configuration
2. please use dataclasses.py for dataclasses


python main.py --config config/twb-to-pbi.yaml --input "examples/twp-to-pbi-example/Tableau/Sales Dashboard.twb" --output output

BIMIGRATOR_LOG_LEVEL=info python main.py --skip-license-check "examples/twp-to-pbi-example/Tableau/Sales Dashboard V1.twb"


pbi-tools compile ./adventureworksdw2020-pbix/pbix -format PBIT -outPath AdvWorksDW2020.pbit