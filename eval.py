from sklearn.metrics import confusion_matrix
import numpy as np
import tensorflow as tf
import os, argparse
import cv2

tf.compat.v1.disable_eager_execution()
mapping = {'normal': 0, 'pneumonia': 1, 'COVID-19': 2}

def eval(sess, graph, testfile, testfolder):
    image_tensor = graph.get_tensor_by_name("input_1:0")
    pred_tensor = graph.get_tensor_by_name("dense_3/Softmax:0")

    y_test = []
    pred = []
    for i in range(len(testfile)):
        line = testfile[i].split()
        x = cv2.imread(os.path.join('data', testfolder, line[1]))
        h, w, c = x.shape
        x = x[int(h/6):, :]
        x = cv2.resize(x, (224, 224))
        x = x.astype('float32') / 255.0
        y_test.append(mapping[line[2]])
        pred.append(np.array(sess.run(pred_tensor, feed_dict={image_tensor: np.expand_dims(x, axis=0)})).argmax(axis=1))
    y_test = np.array(y_test)
    pred = np.array(pred)

    matrix = confusion_matrix(y_test, pred)
    matrix = matrix.astype('float')
    #cm_norm = matrix / matrix.sum(axis=1)[:, np.newaxis]
    print(matrix)
    #class_acc = np.array(cm_norm.diagonal())
    class_acc = [matrix[i,i]/np.sum(matrix[i,:]) if np.sum(matrix[i,:]) else 0 for i in range(len(matrix))]
    print('Sens Normal: {0:.3f}, Pneumonia: {1:.3f}, COVID-19: {2:.3f}'.format(class_acc[0],
                                                                               class_acc[1],
                                                                               class_acc[2]))
    ppvs = [matrix[i,i]/np.sum(matrix[:,i]) if np.sum(matrix[:,i]) else 0 for i in range(len(matrix))]
    print('PPV Normal: {0:.3f}, Pneumonia {1:.3f}, COVID-19: {2:.3f}'.format(ppvs[0],
                                                                             ppvs[1],
                                                                             ppvs[2]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='COVID-Net Evaluation')
    parser.add_argument('--weightspath', default='output', type=str, help='Path to output folder')
    parser.add_argument('--metaname', default='COVIDNet-lr2e-05/model.meta', type=str, help='Name of ckpt meta file')
    parser.add_argument('--ckptname', default='COVIDNet-lr2e-05/model', type=str, help='Name of model ckpts')
    parser.add_argument('--testfile', default='test_COVIDx.txt', type=str, help='Name of testfile')
    parser.add_argument('--testfolder', default='test', type=str, help='Folder where test data is located')

    args = parser.parse_args()

    sess = tf.compat.v1.Session()
    tf.compat.v1.get_default_graph()
    saver = tf.compat.v1.train.import_meta_graph(os.path.join(args.weightspath, args.metaname))
    saver.restore(sess, os.path.join(args.weightspath, args.ckptname))

    graph = tf.compat.v1.get_default_graph()

    file = open(args.testfile, 'r')
    testfile = file.readlines()

    eval(sess, graph, testfile, args.testfolder)
