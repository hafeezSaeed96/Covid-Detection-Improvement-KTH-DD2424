from __future__ import print_function

import tensorflow as tf
import os, argparse, pathlib

from eval import eval
from data import BalanceCovidDataset

parser = argparse.ArgumentParser(description='COVID-Net Training Script')
parser.add_argument('--epochs', default=10, type=int, help='Number of epochs')
parser.add_argument('--lr', default=0.00002, type=float, help='Learning rate')
parser.add_argument('--bs', default=8, type=int, help='Batch size')
parser.add_argument('--weightspath', default='models/COVIDNet-CXR-Large', type=str, help='Path to output folder')
parser.add_argument('--metaname', default='model.meta', type=str, help='Name of ckpt meta file')
parser.add_argument('--ckptname', default='model-8485', type=str, help='Name of model ckpts')
parser.add_argument('--trainfile', default='train_COVIDx2.txt', type=str, help='Name of train file')
parser.add_argument('--testfile', default='test_COVIDx2.txt', type=str, help='Name of test file')
parser.add_argument('--name', default='COVIDNet', type=str, help='Name of folder to store training checkpoints')
parser.add_argument('--datadir', default='data', type=str, help='Path to data folder')
parser.add_argument('--covid_weight', default=12., type=float, help='Class weighting for covid')
parser.add_argument('--covid_percent', default=0.3, type=float, help='Percentage of covid samples in batch')

args = parser.parse_args()

# Parameters
learning_rate = args.lr
batch_size = args.bs
display_step = 1

# output path
outputPath = './output/'
runID = args.name + '-lr' + str(learning_rate)
runPath = outputPath + runID
pathlib.Path(runPath).mkdir(parents=True, exist_ok=True)
print('Output: ' + runPath)

with open(args.trainfile) as f:
    trainfiles = f.readlines()
with open(args.testfile) as f:
    testfiles = f.readlines()

generator = BalanceCovidDataset(data_dir=args.datadir,
                                csv_file=args.trainfile,
                                covid_percent=args.covid_percent,
                                class_weights=[1., 1., args.covid_weight])

with tf.compat.v1.Session() as sess:
    tf.compat.v1.get_default_graph()
    saver = tf.compat.v1.train.import_meta_graph(os.path.join(args.weightspath, args.metaname))

    graph = tf.compat.v1.get_default_graph()

    image_tensor = graph.get_tensor_by_name("input_1:0")
    labels_tensor = graph.get_tensor_by_name("dense_3_target:0")
    sample_weights = graph.get_tensor_by_name("dense_3_sample_weights:0")
    pred_tensor = graph.get_tensor_by_name("dense_3/MatMul:0")
    # loss expects unscaled logits since it performs a softmax on logits internally for efficiency

    # Define loss and optimizer
    loss_op = tf.reduce_mean(tf.compat.v1.nn.softmax_cross_entropy_with_logits_v2(
        logits=pred_tensor, labels=labels_tensor)*sample_weights)
    optimizer = tf.compat.v1.train.AdamOptimizer(learning_rate=learning_rate)
    train_op = optimizer.minimize(loss_op)

    # Initialize the variables
    init = tf.compat.v1.global_variables_initializer()

    # Run the initializer
    sess.run(init)

    # load weights
    saver.restore(sess, os.path.join(args.weightspath, args.ckptname))
    #saver.restore(sess, tf.train.latest_checkpoint(args.weightspath))

    # save base model
    saver.save(sess, os.path.join(runPath, 'model'))
    print('Saved baseline checkpoint')
    print('Baseline eval:')
    eval(sess, graph, testfiles, 'test')

    # Training cycle
    print('Training started')
    total_batch = len(generator)
    progbar = tf.keras.utils.Progbar(total_batch)
    for epoch in range(args.epochs):
        for i in range(total_batch):
            # Run optimization
            batch_x, batch_y, weights = next(generator)
            sess.run(train_op, feed_dict={image_tensor: batch_x,
                                          labels_tensor: batch_y,
                                          sample_weights: weights})
            progbar.update(i+1)

        if epoch % display_step == 0:
            pred = sess.run(pred_tensor, feed_dict={image_tensor:batch_x})
            loss = sess.run(loss_op, feed_dict={pred_tensor: pred,
                                                labels_tensor: batch_y,
                                                sample_weights: weights})
            print("Epoch:", '%04d' % (epoch + 1), "Minibatch loss=", "{:.9f}".format(loss))
            eval(sess, graph, testfiles, 'test')
            saver.save(sess, os.path.join(runPath, 'model'), global_step=epoch+1, write_meta_graph=False)
            print('Saving checkpoint at epoch {}'.format(epoch + 1))


print("Optimization Finished!")
