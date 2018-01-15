#!/usr/bin/env bash

coverage run --source='.' manage.py test rolez --parallel
coverage report -m rolez/*.py