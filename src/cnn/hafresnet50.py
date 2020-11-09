import tensorflow as tf
import numpy as np

from bin.utils.timethis import timethis
from src.cnn.hafmodel import HAFModel
from src.layers.utils import insert_saliency_layers
from src.losses.losses import haf_loss


class HAFResNet50Model(HAFModel):
    def __init__(self, base_model):
        super().__init__(base_model=base_model)

    def insert_saliency_layers(self, layers):
        """
        layers: Where to put the saliency layers
        """
        layer_names = ['saliency_{0}'.format(i) for i in range(len(layers))]

        self.haf_model = insert_saliency_layers(self.base_model, layers, layer_names=layer_names, position='after')

        self.haf_model.layers[-1].activation =  tf.keras.layers.Activation(activation='linear')

    @timethis
    def train(self, data_loader, lr=0.05, epochs=30, reg=0.5):
        """
        lr: learning rate
        epochs: number of epochs
        reg: regularization factor (lambda) in eq.17 of HAF paper
        """

        optimizer = tf.keras.optimizers.Adam(lr=lr)

        for epoch in range(1, epochs + 1):
            dataset = data_loader.dataset.shuffle(buffer_size=data_loader.batch_size * 8)

            for iteration, (imagine, ground_score, ground_class) in enumerate(dataset):
                with tf.GradientTape() as tape:
                    # make a prediction using the model and then calculate the loss
                    full_score_class = self.haf_model(imagine)

                    loss = haf_loss(ground_score, full_score_class, self.haf_model.trainable_variables, reg=reg)

                self.losses.append(loss)
                # calculate the gradients using our tape and then update the model weights
                grads = tape.gradient(loss, self.haf_model.trainable_variables)
                optimizer.apply_gradients(zip(grads, self.haf_model.trainable_variables))

                # Project Gradient Descent
                for i, trainable_variable in enumerate(self.haf_model.trainable_variables):
                    self.haf_model.trainable_variables[i].assign(tf.clip_by_value(trainable_variable, clip_value_min=0,
                                                                                  clip_value_max=np.inf))

                print("Epoch: {} Iteration: {} Loss: {}".format(epoch, iteration + 1, loss))

        print("Train Ended")
