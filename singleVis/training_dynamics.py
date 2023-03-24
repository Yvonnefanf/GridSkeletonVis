"""
A class to record training dynamics, including:
1. loss
2. uncertainty
3. position
4. velocity
5. acceleration
6. hard samples
7. training dynamics
8.
"""
import numpy as np

def softmax(x):
    return np.exp(x) / np.sum(np.exp(x))

def cross_entropy(data, y):
    log_p = np.array([np.log(softmax(data[i])) for i in range(len(data))])
    y_onehot = np.eye(len(data))[y]
    loss = - np.sum(y_onehot * log_p) / len(data)


class TD:
    def __init__(self, data_provider, projector) -> None:
        self.data_provider = data_provider
        self.projector = projector
    
    def loss_dynamics(self, ):
        EPOCH_START = self.data_provider.s
        EPOCH_END = self.data_provider.e
        EPOCH_PERIOD = self.data_provider.p
        labels = self.data_provider.train_labels(EPOCH_START)

        criterion = nn.CrossEntropyLoss()
        criterion(output, batch_y)

        # epoch, num, 1
        uncertainties = None

        for epoch in range(EPOCH_START, EPOCH_END+1, EPOCH_PERIOD):
            representation = self.data_provider.train_representation(epoch)
            pred = self.data_provider.get_pred(epoch, representation)
            idxs = list(enumerate(labels))
            uncertainty = pred[idxs]

            if uncertainties is None:
                uncertainties = np.expand_dims(uncertainty, axis=0)
            else:
                uncertainties = np.concatenate((uncertainties, np.expand_dims(uncertainty, axis=0)), axis=0)
        uncertainties = np.transpose(uncertainties, [1,0,2])
        return uncertainties
    
    def uncertainty_dynamics(self, ):
        EPOCH_START = self.data_provider.s
        EPOCH_END = self.data_provider.e
        EPOCH_PERIOD = self.data_provider.p
        labels = self.data_provider.train_labels(EPOCH_START)

        # epoch, num, 1
        uncertainties = None

        for epoch in range(EPOCH_START, EPOCH_END+1, EPOCH_PERIOD):
            representation = self.data_provider.train_representation(epoch)
            pred = self.data_provider.get_pred(epoch, representation)
            idxs = list(enumerate(labels))
            uncertainty = pred[idxs]

            if uncertainties is None:
                uncertainties = np.expand_dims(uncertainty, axis=0)
            else:
                uncertainties = np.concatenate((uncertainties, np.expand_dims(uncertainty, axis=0)), axis=0)
        uncertainties = np.transpose(uncertainties, [1,0,2])
        return uncertainties
    
    def dloss_dt_dynamics(self, ):
        return
    
    def position_dynamics(self):
        EPOCH_START = self.data_provider.s
        EPOCH_END = self.data_provider.e
        EPOCH_PERIOD = self.data_provider.p

        # epoch, num, dims
        embeddings = None

        for epoch in range(EPOCH_START, EPOCH_END+1, EPOCH_PERIOD):
            representation = self.data_provider.train_representation(epoch)
            embedding = self.projector.batch_project(epoch, representation)
            if embeddings is None:
                embeddings = np.expand_dims(embedding, axis=0)
            else:
                embeddings = np.concatenate((embeddings, np.expand_dims(embedding, axis=0)), axis=0)
        embeddings = np.transpose(embeddings, [1,0,2])
        return embeddings
    
    def velocity_dynamics(self,):
        position_dynamics = self.position_dynamics()
        return position_dynamics[:, 1:, :] - position_dynamics[:, :-1, :]

    def acceleration_dynamics(self, ):
        velocity_dynamics = self.velocity_dynamics()
        return velocity_dynamics[:, 1:, :] - velocity_dynamics[:, :-1, :]
    

    