"""
On this file we have all the utility for managing data
in particular we build a data generator in order to 
load the json one peace at time in order to be able to
compute the training even without more than 16 GB of RAM available
"""
import os
import numpy as np
import tensorflow as tf
import dataset_utils


class DataGenerator(tf.keras.utils.Sequence):
    'Generates data for Keras'

    def __init__(self, directory_path, namemodel, vocab, verbose, evaluate, batch_size=4,
                 max_num_samples=1_000_000_000, validation = False):
        'Initialization'
        '''
        Load the files and create the question answer tuple
        store everithing 
        
        @param batch_size integer for the size of the batch
        @param directory_path path of the directory containing the training files
        @param namemodel name of model to use (bert, albert)
        @param vocab the vocabulary
        @param max_num_samples integer for the maximum number of samples
        '''
        self.validation = validation
        self.Allfiles = os.listdir(directory_path) #list of all the files from the directory
        self.files = self.Allfiles.copy()
        print("\n\nthe file we will use for generator are: {}\n\n".format(self.files))
        self.namefile = self.files.pop()
        print(self.namefile)
        self.path = directory_path
        self.batch_size = batch_size
        self.namemodel = namemodel
        self.vocab = vocab
        self.verbose = verbose
        self.evaluate = evaluate
        self.max_num_samples = max_num_samples
        # loading the first file from the directory which will be used for
        # the first training cycle
        self.input, self.output = dataset_utils.getTokenizedDataset(self.namemodel,
                                                                    self.vocab, 'uncased',
                                                                     os.path.join(self.path, self.namefile),
                                                                    self.verbose,
                                                                    self.evaluate,
                                                                    self.max_num_samples)

    def num_files(self):
        return len(self.Allfiles)

    def __len__(self):
        'Denotes the number of batches per epoch'
        return int(np.floor(len(self.input['attention_mask']) / self.batch_size))

    def __getitem__(self, index):
        'Generate one batch of data'
        '''
        this is the dictionary names for the input and output of the model
         x = {
            'input_ids': 
            'attention_mask':
            'token_type_ids':
        }
        y = {
            'start': 
            'end':
            'type':         
        }
        '''
        x = {k: v[self.batch_size * index:self.batch_size * (index + 1)] for k, v in self.input.items()}

        y = [v[self.batch_size * index:self.batch_size * (index + 1)] for v in self.output]

        return x, y

    def on_epoch_end(self):
        # change the current file and add it to the done list
        if not self.validation:
            if not self.files:
                self.files = self.Allfiles
            self.namefile = self.files.pop()
            print("New file: " + self.namefile)
            
            # update the input and output tensors for this epoch 
            self.input, self.output = dataset_utils.getTokenizedDataset(self.namemodel,
                                                            self.vocab, 'uncased',
                                                            os.path.join(self.path, self.namefile),
                                                            self.verbose,
                                                            self.evaluate,
                                                            self.max_num_samples)
            
