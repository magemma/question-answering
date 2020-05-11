from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from datetime import datetime
from sys import platform
from dataset_utils import *

from model_stuff.TFAlbertForNaturalQuestionAnswering import TFAlbertForNaturalQuestionAnswering
from model_stuff.TFBertForNaturalQuestionAnswering import TFBertForNaturalQuestionAnswering
from model_stuff import model_utils as mu


def main(namemodel, args, checkpoint, namefile, verbose=False, max_num_samples=1_000_000, do_cache=False):
    """
    :param do_cache:
    :param namefile:
    :param args:
    :param checkpoint:
    :param namemodel: nomde del modello da eseguire
    :param verbose: fag per stampare informazioni sul primo elemento del datasetk
    :param max_num_samples: massimo numero di oggetti da prendere in considerazione (1mil Default)
    :return: TUTTO

    """

    if platform == "win32":
        logs = "logs\\" + datetime.now().strftime("%Y%m%d-%H%M%S")  # Windows
    else:
        logs = "log/" + datetime.now().strftime("%Y%m%d-%H%M%S")  # Linux

    if not os.path.exists(logs):
        os.makedirs(logs)


    MODEL_CLASSES = {
        'bert': (BertConfig, TFBertForNaturalQuestionAnswering, BertTokenizer),
        'bert_large': (BertConfig, TFBertForNaturalQuestionAnswering, BertTokenizer),
        'albert': (AlbertConfig, TFAlbertForNaturalQuestionAnswering, AlbertTokenizer),  # V2
        'albert_squad': (AlbertConfig, TFAlbertForNaturalQuestionAnswering,
                         AutoTokenizer.from_pretrained("twmkn9/albert-base-v2-squad2"))
        # 'roberta': (RobertaConfig, TFRobertaForNaturalQuestionAnswering, RobertaTokenizer),
    }

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
    elif namemodel == "albert_squad":
        model_config = 'input/transformers_cache/albert_base_v2_squad.json'
        vocab = 'input/transformers_cache/albert-base-v2-spiece.model'
    elif namemodel == "bert_large":
        model_config = 'input/transformers_cache/bert_large_uncased_config.json'
        vocab = 'input/transformers_cache/bert_large_uncased_vocab.txt'
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

    mymodel = model_class(config)

    mymodel(mymodel.dummy_inputs, training=False)

    mymodel.load_weights(checkpoint, by_name=True)
    print("Checkpoint loaded succefully")

    print("***** Running evaluation *****")
    tokenizer = tokenizer_class(vocab, do_lower_case='uncased')

    tokenizer = tokenizer_class.from_pretrained("albert-base-v2",
        do_lower_case=do_lower_case)
    #tags = get_add_tokens(do_enumerate=args.do_enumerate)
    #num_added = tokenizer.add_tokens(tags)
    #print(f"Added {num_added} tokens")
    eval_ds, crops, entries, eval_dataset_length = getDatasetForEvaluation(args, tokenizer, namefile, verbose,
                                                                           max_num_samples, do_cache)
    print("***** Getting results *****")
    result = getResult(args, mymodel, eval_ds, crops, entries, eval_dataset_length, do_cache, namefile,tokenizer)
    print("Result: {}".format(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

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

    parser.add_argument("--checkpoint", default="checkpoints/checkpoint-031000/weights.h5", type=str, help="The file we will use as checkpoint")

    parser.add_argument('--test_dir', type=str, default='TestData/simplified-nq-test.jsonl',
                        help='Directory were all the traing data splitted in smaller junks are stored')

    parser.add_argument('--epoch', type=int, default=1)
    parser.add_argument('--model', type=str, default='albert')
    parser.add_argument('--batch_size', type=int, default=4)
    parser.add_argument('--verbose', type=bool, default=False)
    parser.add_argument('--do_cache', type=bool, default=False)

    args, _ = parser.parse_known_args()

    print("File for evaluation: ", args.test_dir)
    # assert args.checkpoint.endswith('.hdf5'), "Checkpoint not specified"
    print("Checkpoint for evaluation: ", args.checkpoint)
    print("Evaluation parameters ", args)

    main(args.model, args, args.checkpoint, args.test_dir, verbose=args.verbose, do_cache=args.do_cache)
