"""
In this file we store all class for the models 
tensorflow 2.0

{
  "attention_probs_dropout_prob": 0.1,
  "bos_token_id": 0,
  "do_sample": false,
  "eos_token_ids": 0,
  "finetuning_task": null,
  "hidden_act": "gelu",
  "hidden_dropout_prob": 0.1,
  "hidden_size": 1024,
  "id2label": {
    "0": "LABEL_0",
    "1": "LABEL_1"
  },
  "initializer_range": 0.02,
  "intermediate_size": 4096,
  "is_decoder": false,
  "label2id": {
    "LABEL_0": 0,
    "LABEL_1": 1
  },
  "layer_norm_eps": 1e-12,
  "length_penalty": 1.0,
  "max_length": 20,
  "max_position_embeddings": 512,
  "num_attention_heads": 16,
  "num_beams": 1,
  "num_hidden_layers": 24,
  "num_labels": 2,
  "num_return_sequences": 1,
  "output_attentions": false,
  "output_hidden_states": false,
  "output_past": true,
  "pad_token_id": 0,
  "pruned_heads": {},
  "repetition_penalty": 1.0,
  "temperature": 1.0,
  "top_k": 50,
  "top_p": 1.0,
  "torchscript": false,
  "type_vocab_size": 2,
  "use_bfloat16": false,
  "vocab_size": 30522
}
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import os
import re
from datetime import datetime
import tensorflow as tf
from transformers import BertConfig, BertTokenizer, AlbertTokenizer, AlbertConfig
from generator import DataGenerator
from model_stuff import model_utils as mu
from model_stuff.TFAlbertForNaturalQuestionAnswering import TFAlbertForNaturalQuestionAnswering
from model_stuff.TFBertForNaturalQuestionAnswering import TFBertForNaturalQuestionAnswering


def main(namemodel, batch_size, train_dir, val_dir, epoch, checkpoint_dir, verbose=False, evaluate=False,
         max_num_samples=1_000_000, checkpoint="", log_dir="log/"):
    """

    :param log_dir:
    :param checkpoint:
    :param epoch:
    :param train_dir:
    :param val_dir:
    :param checkpoint_dir:
    :param namemodel: nomde del modello da eseguire
    :param batch_size: dimensione del batch durante il training
    :param verbose: fag per stampare informazioni sul primo elemento del dataset
    :param evaluate: Bool per indicare se dobbiamo eseguire Evaluation o Training. Training di Default
    :param max_num_samples: massimo numero di oggetti da prendere in considerazione (1mil Default)
    :return: TUTTO

    """
    logs = os.path.join(log_dir, datetime.now().strftime("%Y%m%d-%H%M%S"))  # Linux
    # logs = "logs\\" + datetime.now().strftime("%Y%m%d-%H%M%S")  # Windows
    if not os.path.exists(logs):
        os.makedirs(logs)
    tboard_callback = tf.keras.callbacks.TensorBoard(log_dir=logs,
                                                     histogram_freq=1,
                                                     update_freq='batch',
                                                     profile_batch=0)

    MODEL_CLASSES = {
        'bert': (BertConfig, TFBertForNaturalQuestionAnswering, BertTokenizer),
        'albert': (AlbertConfig, TFAlbertForNaturalQuestionAnswering, AlbertTokenizer),  # V2
        # 'roberta': (RobertaConfig, TFRobertaForNaturalQuestionAnswering, RobertaTokenizer),
    }
    dictionary = False
    if dictionary:
        losses = {
            "start": "categorical_crossentropy",
            "end": "categorical_crossentropy",
            "type": "categorical_crossentropy",
        }

        lossWeights = {"start": 1.0, "end": 1.0, "type": 1.0}

    else:
        losses = ["categorical_crossentropy", "categorical_crossentropy", "categorical_crossentropy"]
        lossWeights = [1.0, 1.0, 1.0]

    do_lower_case = 'uncased'
    if namemodel == "bert":  # base
        model_config = 'input/transformers_cache/bert_base_uncased_config.json'
        vocab = 'input/transformers_cache/bert_base_uncased_vocab.txt'
    elif namemodel == 'albert':  # base v2
        model_config = 'input/transformers_cache/albert_base_v2.json'
        vocab = 'input/transformers_cache/albert-base-v2-spiece.model'
    elif namemodel == 'roberta':
        do_lower_case = False
        model_config = 'lo aggiungero in futuro'
        vocab = 'lo aggiungero in futuro'
    else:
        # di default metto il base albert
        model_config = 'input/transformers_cache/albert_base_v2.json'
        vocab = 'input/transformers_cache/albert-base-v2-spiece.model'
        namemodel = "albert"
        print("sei impazzuto?")

    # Set XLA
    # https://github.com/kamalkraj/ALBERT-TF2.0/blob/8d0cc211361e81a648bf846_d8ec84225273db0e4/run_classifer.py#L136
    tf.config.optimizer.set_jit(True)
    tf.config.optimizer.set_experimental_options({'pin_to_host_optimization': False})

    config_class, model_class, tokenizer_class = MODEL_CLASSES[namemodel]
    config = config_class.from_json_file(model_config)

    print(model_class)
    mymodel = model_class(config)

    mymodel(mymodel.dummy_inputs)

    if checkpoint != "":
        # we do this in order to compile the model, otherwise it will not be able to lead the weights
        # mymodel(traingenerator.get_sample_data())
        startepoch = os.path.split(checkpoint)[-1]
        startepoch = re.sub('weights.', '', startepoch)
        startepoch = int(startepoch.split("-")[0])

        mymodel.load_weights(checkpoint, by_name=True)
        print("checkpoint loaded succefully")
    else:
        startepoch = None

    adam = tf.keras.optimizers.Adam(lr=0.05)

    mymodel.compile(loss=losses,
                    loss_weights=lossWeights,
                    metrics=['categorical_accuracy'],
                    optimizer=adam
                    )

    # data generator creation:
    # validation 
    print(val_dir)
    print(train_dir)

    validation_generator = DataGenerator(val_dir, namemodel, vocab, verbose, evaluate, batch_size=batch_size,
                                         validation=True)

    traingenerator = DataGenerator(train_dir, namemodel, vocab, verbose, evaluate, batch_size=batch_size,
                                   batch_start=startepoch)

    # Training data
    # since we do an epoch for each file eventually we have to do 
    # epoch*n_files epochs
    n_files = traingenerator.num_files()
    if startepoch:
        epoch = (int(epoch) - 1) * n_files + (n_files - startepoch)
    else:
        epoch = int(epoch) * n_files

    print('\n\nwe have {} files so we will train for {} epochs\n\n'.format(n_files, epoch))

    cb = mu.TimingCallback()  # execution time callback

    cp_freq = 1000
    filepath = os.path.join(checkpoint_dir, "weights.{epoch:02d}-{loss:.2f}.hdf5")
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    checkpoint = tf.keras.callbacks.ModelCheckpoint(filepath,
                                                    save_weights_only=False,
                                                    monitor='categorical_accuracy',
                                                    verbose=0,
                                                    save_freq="epoch")

    # callbacks
    callbacks_list = [cb, tboard_callback, checkpoint]

    # fitting
    mymodel.fit(traingenerator, validation_data=validation_generator, verbose=1, epochs=epoch, callbacks=callbacks_list)
    mymodel.summary()
    print("Time: " + str(cb.logs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # LARGE BERT
    # parser.add_argument("--model_config", default="input/transformers_cache/bert_large_uncased_config.json", type=str)
    # parser.add_argument("--vocab_txt", default="input/transformers_cache/bert_large_uncased_vocab.txt", type=str)

    # Other parameters
    parser.add_argument('--short_null_score_diff_threshold', type=float, default=0.0)
    parser.add_argument('--long_null_score_diff_threshold', type=float, default=0.0)
    parser.add_argument("--max_seq_length", default=512, type=int)
    parser.add_argument("--doc_stride", default=256, type=int)
    parser.add_argument("--max_query_length", default=64, type=int)
    parser.add_argument("--per_tpu_eval_batch_size", default=4, type=int)
    parser.add_argument("--n_best_size", default=10, type=int)
    parser.add_argument("--max_answer_length", default=30, type=int)
    parser.add_argument("--verbose_logging", action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--p_keep_impossible', type=float,
                        default=0.1, help="The fraction of impossible"
                                          " samples to keep.")
    parser.add_argument('--do_enumerate', action='store_true')

    parser.add_argument("--checkpoint_dir", default="checkpoints/", type=str,
                        help="the directory where we want to save the checkpoint")
    parser.add_argument("--checkpoint", default="", type=str, help="The file we will use as checkpoint")

    parser.add_argument('--validation_dir', type=str, default='validationData/',
                        help='Directory where all the validation data splitted in smaller junks are stored')
    parser.add_argument('--train_dir', type=str, default='TrainData/',
                        help='Directory where all the traing data splitted in smaller junks are stored')

    parser.add_argument('--log_dir', type=str, default='log/',
                        help='Directory for tensorboard')

    parser.add_argument('--epoch', type=int, default=1)
    parser.add_argument('--model', type=str, default='albert')
    parser.add_argument('--batch_size', type=int, default=4)
    parser.add_argument('--evaluate', type=bool, default=False)
    parser.add_argument('--verbose', type=bool, default=False)

    args, _ = parser.parse_known_args()
    # assert args.model_type not in ('xlnet', 'xlm'), f'Unsupported model_type: {args.model_type}'
    print("Training / evaluation parameters %s", args)

    main(args.model, args.batch_size, args.train_dir, args.validation_dir, args.epoch, args.checkpoint_dir,
         checkpoint=args.checkpoint,
         evaluate=args.evaluate, verbose=args.verbose, log_dir=args.log_dir)
