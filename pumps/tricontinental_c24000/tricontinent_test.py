#import sys
#sys.path.append('../')
from methods import GeneralExperimentMethod

experiment = GeneralExperimentMethod(
    input_file="tricontinental_test_instrument_config.csv",
    instrument_config_file="tricontinental_test_method.csv"
)
experiment.run_experiment()