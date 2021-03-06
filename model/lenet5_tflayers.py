from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Imports
import numpy as np
import tensorflow as tf
import os

from tensorflow.contrib import learn
from tensorflow.python.ops import array_ops
from tensorflow.python.ops import template
from misc.datasets import MnistDataset
from progressbar import ETA, Bar, Percentage, ProgressBar
import functools

tf.logging.set_verbosity(tf.logging.INFO)

tf.app.flags.DEFINE_string(
    'save_path', '/Users/huixu/Documents/codelabs/alphabet2cla/logs_test/', 'Where to save the model checkpoints.')
tf.app.flags.DEFINE_string('log_dir', '/Users/huixu/Documents/codelabs/alphabet2cla/logs_test/',
                           'Where to save the logs for visualization in TensorBoard.')
FLAGS = tf.app.flags.FLAGS

BATCH_SIZE = 676
BATCH_PER_EPOCH = 52832 // BATCH_SIZE
EPOCH_SIZE = 50
LEARNING_RATE = 1E-4

# Our application logic will be added here

def conv_layer(input, size_in, size_out):
    #with tf.name_scope(name):
    w = tf.get_variable(initializer=tf.truncated_normal([5, 5, size_in, size_out], stddev=0.1), name="W")
    b = tf.get_variable(initializer=tf.constant(0.1, shape=[size_out]), name="B")
    conv = tf.nn.conv2d(input, w, strides=[1, 1, 1, 1], padding="SAME")
    #nor_conv = normalization_layers.BatchNormalization().apply(conv, training=training)
    act = tf.nn.relu(conv + b)
    #act = tf.nn.relu(nor_conv + b)
    tf.summary.histogram("weights", w)
    tf.summary.histogram("bias", b)
    tf.summary.histogram("activations", act)
    #return tf.nn.max_pool(act, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding="SAME")
    return act

def fc_layer(input, size_in, size_out):
    #with tf.name_scope(name):
    w = tf.get_variable(initializer=tf.truncated_normal([size_in, size_out], stddev=0.1), name="W")
    b = tf.get_variable(initializer=tf.constant(0.1, shape=[size_out]), name="B")
    act = tf.nn.relu(tf.matmul(input, w) + b)
    #act = tf.nn.relu( normalization_layers.BatchNormalization().apply( tf.matmul(input, w) + b,  training=training) )
    tf.summary.histogram("weights", w)
    tf.summary.histogram("bias", b)
    tf.summary.histogram("activations", act)
    return act

def doublewrap(function):
    """
    A decorator decorator, allowing to use the decorator to be used without parentheses
    if not arguments are provided. All arguments must be optional.
    """
    @functools.wraps(function)
    def decorator(*args, **kwargs):
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            return function(args[0])
        else:
            return lambda wrapee: function(wrapee, *args, **kwargs)
    return decorator

@doublewrap
def define_scope(function, scope=None, *args, **kwargs):
    """
    A decorator for functions that define TensorFlow operations. The wrapped
    function will only be executed once. Subsequent calls to it will directly
    return the result so that operations are added to the graph only once.

    The operations added by the function live within a tf.variable_scope(). If
    this decorator is used with arguments, they will be forwarded to the variable
    scope. The scope name defaults to the name of the wrapped function.
    """
    attribute = '_cache_' + function.__name__
    name = scope or function.__name__
    @property
    @functools.wraps(function)
    def decorator(self):
        if not hasattr(self, attribute):
            with tf.variable_scope(name, *args, **kwargs):
                #https://www.tensorflow.org/programmers_guide/variable_scope#initializers_in_variable_scope
                setattr(self, attribute, function(self))
        return getattr(self, attribute)
    return decorator

class Model:
    def __init__(self, image, label, is_train, params):
    	self.image = image
        self.label = label
        self.is_train = is_train
        self.lr = params["learning_rate"]
        self.global_step = tf.get_variable(name='global_step', shape=[], initializer=tf.constant_initializer(0), dtype=tf.int32, trainable=False)
        self.net_forward
        self.inference
        self.loss
        self.prediction
        self.optimize
        self.accuracy
        self.embedding
        self.embedding_name


    @define_scope
    def net_forward(self):
        # Input Layer
        # Reshape X to 4-D tensor: [batch_size, width, height, channels]
        # MNIST images are 28x28 pixels, and have one color channel
        input_layer = tf.reshape(self.image, [-1, 28, 28, 1])
        tf.summary.image('input', input_layer, 3)
        # Convolutional Layer #1
        # Computes 32 features using a 5x5 filter with ReLU activation.
        # Padding is added to preserve width and height.
        # Input Tensor Shape: [batch_size, 28, 28, 1]
        # Output Tensor Shape: [batch_size, 28, 28, 32]
        #conv1 = tf.layers.conv2d(inputs=input_layer,filters=32,kernel_size=[5, 5],padding="same",activation=tf.nn.relu)
        with tf.variable_scope("conv1"):
            conv1 = conv_layer(input_layer, 1, 20)

        # Pooling Layer #1
        # First max pooling layer with a 2x2 filter and stride of 2
        # Input Tensor Shape: [batch_size, 28, 28, 32]
        # Output Tensor Shape: [batch_size, 14, 14, 32]
        pool1 = tf.layers.max_pooling2d(inputs=conv1, pool_size=[2, 2], strides=2, padding='same', name="pool1")

        # Convolutional Layer #2
        # Computes 64 features using a 5x5 filter.
        # Padding is added to preserve width and height.
        # Input Tensor Shape: [batch_size, 14, 14, 32]
        # Output Tensor Shape: [batch_size, 14, 14, 64]
        #conv2 = tf.layers.conv2d(inputs=pool1,filters=64,kernel_size=[5, 5],padding="same",activation=tf.nn.relu)
        with tf.variable_scope("conv2"):
            conv2 = conv_layer(pool1, 20, 50)

        # Pooling Layer #2
        # Second max pooling layer with a 2x2 filter and stride of 2
        # Input Tensor Shape: [batch_size, 14, 14, 64]
        # Output Tensor Shape: [batch_size, 7, 7, 64]
        pool2 = tf.layers.max_pooling2d(inputs=conv2, pool_size=[2, 2], strides=2, padding='same', name="pool2")

        # Flatten tensor into a batch of vectors
        # Input Tensor Shape: [batch_size, 7, 7, 64]
        # Output Tensor Shape: [batch_size, 7 * 7 * 64]
        pool2_flat = tf.reshape(pool2, [-1, 7 * 7 * 50])
        # Dense Layer
        # Densely connected layer with 1024 neurons
        # Input Tensor Shape: [batch_size, 7 * 7 * 64]
        # Output Tensor Shape: [batch_size, 1024]
        #dense = tf.layers.dense(inputs=pool2_flat, units=1024, activation=tf.nn.relu)
        with tf.variable_scope("fc1"):
            dense = fc_layer(pool2_flat, 7 * 7 * 50, 500)
        """
        # Add dropout operation; 0.6 probability that element will be kept
        dropout = tf.layers.dropout(inputs=dense, rate=0.4, training=self.is_train)

        # Logits layer
        # Input Tensor Shape: [batch_size, 1024]
        # Output Tensor Shape: [batch_size, 10]
        #logits = tf.layers.dense(inputs=dropout, units=10)
        with tf.variable_scope("fc2"):
            logits = fc_layer(dropout, 1024, 52)

        forward_out = {"logits": logits, "embedding_input": dense, "embedding_size": 1024}
        """
        return dense

    @define_scope
    def inference(self):
        # Add dropout operation; 0.6 probability that element will be kept
        dropout = tf.layers.dropout(inputs=self.net_forward, rate=0.4, training=self.is_train)

        # Logits layer
        # Input Tensor Shape: [batch_size, 1024]
        # Output Tensor Shape: [batch_size, 10]
        #logits = tf.layers.dense(inputs=dropout, units=10)
        with tf.variable_scope("fc2"):
            logits = fc_layer(dropout, 500, 52)

        return logits

    @define_scope
    def prediction(self):
        # Generate Predictions
        prob = tf.nn.softmax(self.inference, name="softmax_tensor")
        """
        cla = tf.argmax(input=prob, axis=1)
        predictions = {
            "classes": cla,
            "probabilities": prob
        }
        """
        return prob

    @define_scope
    def loss(self):
        xent = tf.reduce_mean(
            tf.nn.sparse_softmax_cross_entropy_with_logits(
                logits=self.inference, labels=self.label), name="xent")
        tf.summary.scalar("loss", xent)
        return xent

    @define_scope
    def optimize(self):
        optimizer = tf.train.AdamOptimizer(self.lr)
        return optimizer.minimize(self.loss, global_step=self.global_step)

    @define_scope
    def accuracy(self):
        correct_prediction = tf.equal(self.label, tf.argmax(self.prediction, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
        tf.summary.scalar("accuracy", accuracy)
        return accuracy

    @define_scope
    def embedding(self):
        embedding = tf.get_variable(initializer=tf.zeros([BATCH_SIZE, 500]), name="test_embedding")
        self.embedding_name = embedding.name
        # first 1024 is  Number of items, self.net_forward["embedding_size"] is dimensionality of the embedding
        assignment = embedding.assign(self.net_forward)
        return assignment


def main(_=None):
    # Set model params
    model_params = {"learning_rate": LEARNING_RATE}
    # Training data, nodes in a graph
    is_train = tf.placeholder(tf.bool, name="is_train")
    #is_train_data = tf.placeholder(tf.bool, name="is_train_data")
    #data_type = tf.placeholder_with_default(0, [], name="data_type")
    dataset = MnistDataset(BATCH_SIZE)
    #train_batch = dataset.gen_img_next_batch(dataset.get_gen_image(dataset.tfrecord_filename), BATCH_SIZE)
    train_batch_imgs, train_batch_labels = dataset.get_train_batch_images()
    #_batch_imgs, _batch_labels = tf.identity(train_batch_imgs), tf.identity(train_batch_labels)
    #embedding_imgs, embedding_labels = dataset.get_embedding_images()
    dataset.get_embedding_images()
    # Embedding, eval data, numpy array
    #embedding_imgs, embedding_labels = dataset.generate_sprite()

    #_batch_imgs, _batch_labels = dataset.input_switch(is_train_data)

    #model = Model(is_train, model_params)


    #x = tf.placeholder(tf.float32, shape=[None, 784], name="x")
    #y = tf.placeholder(tf.int64, shape=[None], name="labels")

    #model = Model(x, y, is_train, model_params)
    #model = Model(_batch_imgs, _batch_labels, is_train, model_params)
    model = Model(train_batch_imgs, train_batch_labels, is_train, model_params)
    #https://github.com/tensorflow/tensorflow/blob/master/tensorflow/python/ops/template.py
    #model_template = template.make_template("nn_model",Model, is_train=is_train, params=model_params)

    #train_model = model_template(train_batch_imgs, train_batch_labels)
    #valid_model = model_template(valid_batch_imgs, valid_batch_labels)



    # Format: tensorflow/contrib/tensorboard/plugins/projector/projector_config.proto
    config = tf.contrib.tensorboard.plugins.projector.ProjectorConfig()
    # You can add multiple embeddings. Here we add only one.
    embedding_config = config.embeddings.add()
    embedding_config.tensor_name = model.embedding_name

    # Link this tensor to its metadata file (e.g. labels).
    embedding_config.sprite.image_path = FLAGS.log_dir + 'sprite_1024.png'
    embedding_config.metadata_path = FLAGS.log_dir + 'labels_1024.tsv'
    # Specify the width and height of a single thumbnail
    embedding_config.sprite.single_image_dim.extend([28, 28])

    # Use the same LOG_DIR where you stored your checkpoint.
    summary_writer = tf.summary.FileWriter(FLAGS.log_dir)

    # The next line writes a projector_config.pbtxt in the LOG_DIR. TensorBoard will
    # read this file during startup.
    tf.contrib.tensorboard.plugins.projector.visualize_embeddings(summary_writer, config)

    sess = tf.InteractiveSession()

    init_op = tf.group(tf.global_variables_initializer(), tf.local_variables_initializer())
    sess.run(init_op)


    summ = tf.summary.merge_all()


    saver = tf.train.Saver()

    ckpt = tf.train.get_checkpoint_state(FLAGS.save_path)
    if ckpt and ckpt.model_checkpoint_path:
        saver.restore(sess, ckpt.model_checkpoint_path)
        print('restore ckpt from %s', ckpt.model_checkpoint_path)

    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess,coord=coord)


    widgets = ["epoch #%d|" % 1, Percentage(), Bar(), ETA()]
    pbar = ProgressBar(maxval=EPOCH_SIZE, widgets=widgets)
    pbar.start()
    #summary_writer.add_graph(sess.graph)

    for e in range(EPOCH_SIZE):
        #pbar.update(e)
        #print(model.global_step.eval())
        #print(sess.run(_batch_labels))
        for i in range(BATCH_PER_EPOCH):
            #train_images, train_labels = sess.run([train_batch_xs, train_batch_ys]) # is it fetch different data everytime? yes
            #global_step_num = (e+1)*i
            global_step_num = model.global_step.eval()

            if  global_step_num % 5 == 0:
                pbar.update(global_step_num)
                #[train_accuracy, s] = sess.run([model.accuracy, summ], feed_dict={x: train_images, y: train_labels, is_train:False})
                [train_accuracy, s] = sess.run([model.accuracy, summ], feed_dict={is_train:False})
                summary_writer.add_summary(s, i)
                #print(i,'-',train_accuracy)
            if global_step_num % 500 == 0:
                #sess.run(model.embedding, feed_dict={x: embedding_imgs, y:embedding_labels, is_train:False})
                #print(sess.run(valid_batch_labels))
                # check whether numpy ndarray embedding_labels has been feeded into Tensor train_batch_labels
                #print(sess.run(_batch_labels, feed_dict={train_batch_labels:embedding_labels}))
                sess.run(model.embedding, feed_dict={is_train:False, train_batch_imgs:dataset.embedding_imgs, train_batch_labels:dataset.embedding_labels})
                #embedding_imgs_accuracy = sess.run(model.accuracy, feed_dict={x: embedding_imgs, y:embedding_labels, is_train:False})
                embedding_imgs_accuracy = sess.run(model.accuracy, feed_dict={is_train:False, train_batch_imgs:dataset.embedding_imgs, train_batch_labels:dataset.embedding_labels})
                #print(embedding_imgs_accuracy)

                saver.save(sess, os.path.join(FLAGS.save_path, "model.ckpt"), global_step=model.global_step)
                summary_writer.add_graph(sess.graph)

            #sess.run(model.optimize, feed_dict={x: train_images, y: train_labels, is_train:True})
            sess.run(model.optimize, feed_dict={is_train:True})

    coord.request_stop()
    coord.join(threads)
    summary_writer.close()
    sess.close()

if __name__ == "__main__":
    tf.app.run()
