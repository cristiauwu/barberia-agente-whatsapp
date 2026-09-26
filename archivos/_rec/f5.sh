set -e
K=$(printenv AUTHENTICATION_API_KEY)
echo "key len ${#K}"
wget -qO- --header="apikey: $K" http://evolution_api:8080/instance/connectionState/hector
echo ""