from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv

# UAT
nubra = InitNubraSdk(NubraEnv.UAT)

# PROD
nubra = InitNubraSdk(NubraEnv.PROD)
