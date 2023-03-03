#!/bin/bash
piccolo migrations forwards session_auth
piccolo migrations forwards user
piccolo user create --username=cal-admin --email=chris.immel@gmail.com --password=$CALLIOPE_ADMIN_PASSWORD --is_admin=true --is_superuser=true --is_active=true --trace
