#!/bin/bash

# to activate this outside of the script you need to call like this:

# source ./activate_venv.sh 

echo $VIRTUAL_ENV

if [[ "$VIRTUAL_ENV" == "" ]]
then
    # Activate the virtual environment
    echo "Activating the virtual environment..."
    . venv/bin/activate

    echo $VIRTUAL_ENV
fi


# linux
# . venv/bin/activate

# windows gitbash
#source venv/Scripts/activate
