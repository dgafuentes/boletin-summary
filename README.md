# boletin-summary
Send a csv file with the last ingested values corresponding to boletin feed

## Instalation

You need to create a virtual environment and install the dependencies:

```bash
python -m venv .venv
\.venv\Scripts\activate #  In linux: source .venv/bin/activate
pip install .
```

## Execution

All the configurations to email process are in the code, you must to change values as you needed, all the email configuration is in __EMAIL_CONFIG__ dictionary:

```bash
python boletin_summary.py
```

> [!TIP]
> You can comment __setup_database__ function in *__main__* execution block to can process all feeds more faster, that function is responsible to setup tables in case those do not exist. Also you can add to *__main__* execution block __delete_items__ function to can delete some indicators in all tables (that function was made with test purposes)