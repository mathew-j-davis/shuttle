#!/bin/bash

echo $VIRTUAL_ENV

if [[ "$VIRTUAL_ENV" == ""]]
then
    # Activate the virtual environment
    echo "Activating the virtual environment..."
    . venv/bin/activate
fi

echo $VIRTUAL_ENV


# windows gitbash
#source venv/Scripts/activate
