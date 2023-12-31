from abc import ABC, abstractmethod
import torch
from torch import nn
from singleVis.backend import convert_distance_to_probability, compute_cross_entropy
from singleVis.projector import PROCESSProjector

import torch
torch.manual_seed(0)  # 使用固定的种子
torch.cuda.manual_seed_all(0)
# Set the random seed for numpy

"""Losses modules for preserving four propertes"""
# https://github.com/ynjnpa/VocGAN/blob/5339ee1d46b8337205bec5e921897de30a9211a1/utils/stft_loss.py for losses module

class Loss(nn.Module):
    def __init__(self) -> None:
        super().__init__()
    
    @abstractmethod
    def forward(self, *args, **kwargs):
        pass

class UmapLoss(nn.Module):
    def __init__(self, negative_sample_rate, device, _a=1.0, _b=1.0, repulsion_strength=1.0):
        super(UmapLoss, self).__init__()

        self._negative_sample_rate = negative_sample_rate
        self._a = _a,
        self._b = _b,
        self._repulsion_strength = repulsion_strength
        self.DEVICE = torch.device(device)

    @property
    def a(self):
        return self._a[0]

    @property
    def b(self):
        return self._b[0]

    def forward(self, embedding_to, embedding_from):
        batch_size = embedding_to.shape[0]
        # get negative samples
        embedding_neg_to = torch.repeat_interleave(embedding_to, self._negative_sample_rate, dim=0)
        repeat_neg = torch.repeat_interleave(embedding_from, self._negative_sample_rate, dim=0)
        randperm = torch.randperm(repeat_neg.shape[0])
        embedding_neg_from = repeat_neg[randperm]
        

        #  distances between samples (and negative samples)
        distance_embedding = torch.cat(
            (
                torch.norm(embedding_to - embedding_from, dim=1),
                torch.norm(embedding_neg_to - embedding_neg_from, dim=1),
            ),
            dim=0,
        )
        probabilities_distance = convert_distance_to_probability(
            distance_embedding, self.a, self.b
        )
        probabilities_distance = probabilities_distance.to(self.DEVICE)

        # set true probabilities based on negative sampling
        probabilities_graph = torch.cat(
            (torch.ones(batch_size), torch.zeros(batch_size * self._negative_sample_rate)), dim=0,
        )
        probabilities_graph = probabilities_graph.to(device=self.DEVICE)

        # compute cross entropy
        (_, _, ce_loss) = compute_cross_entropy(
            probabilities_graph,
            probabilities_distance,
            repulsion_strength=self._repulsion_strength,
        )

        return torch.mean(ce_loss)

"""
use fixed negative sample
"""
class UmapLossfix_neg(nn.Module):
    def __init__(self, negative_sample_rate, device, _a=1.0, _b=1.0, repulsion_strength=1.0):
        super(UmapLossfix_neg, self).__init__()

        self._negative_sample_rate = negative_sample_rate
        self._a = _a,
        self._b = _b,
        self._repulsion_strength = repulsion_strength
        self.DEVICE = torch.device(device)

    @property
    def a(self):
        return self._a[0]

    @property
    def b(self):
        return self._b[0]

    def forward(self, embedding_to, embedding_from, edge_to_pred, edge_from_pred):
       

        batch_size = embedding_to.shape[0]
        # get negative samples
        embedding_neg_to = torch.repeat_interleave(embedding_to, self._negative_sample_rate, dim=0)
        repeat_neg = torch.repeat_interleave(embedding_from, self._negative_sample_rate, dim=0)
        randperm = torch.randperm(repeat_neg.shape[0])
        embedding_neg_from = repeat_neg[randperm]

        pred_neg_to = torch.repeat_interleave(edge_to_pred, self._negative_sample_rate, dim=0)
        pred_neg_from = torch.repeat_interleave(edge_from_pred, self._negative_sample_rate, dim=0)[randperm]

    
        #TODO  select better stategy select the prediction cosine distance >0.5 as negative samples
        prediction_diff = torch.abs(pred_neg_to - pred_neg_from)
        valid_neg_indices = torch.where(prediction_diff > 0.5)[0]
        embedding_neg_to = embedding_neg_to[valid_neg_indices]
        embedding_neg_from = embedding_neg_from[valid_neg_indices]
      
        #  distances between samples (and negative samples)
        distance_embedding = torch.cat(
            (
                torch.norm(embedding_to - embedding_from, dim=1),
                torch.norm(embedding_neg_to - embedding_neg_from, dim=1),
            ),
            dim=0,
        )
        probabilities_distance = convert_distance_to_probability(
            distance_embedding, self.a, self.b
        )
        probabilities_distance = probabilities_distance.to(self.DEVICE)

        num_neg_samples = embedding_neg_to.shape[0]  # valied negative samples
        # set true probabilities based on negative sampling
        probabilities_graph = torch.cat(
            (torch.ones(batch_size), torch.zeros(num_neg_samples)), dim=0,
        )
        probabilities_graph = probabilities_graph.to(device=self.DEVICE)

        # compute cross entropy
        (_, _, ce_loss) = compute_cross_entropy(
            probabilities_graph,
            probabilities_distance,
            repulsion_strength=self._repulsion_strength,
        )

        return torch.mean(ce_loss)

# class ReconstructionLoss(nn.Module):
#     def __init__(self, beta=1.0):
#         super(ReconstructionLoss, self).__init__()
#         self._beta = beta

#     def forward(self, edge_to, edge_from, recon_to, recon_from, a_to, a_from):
#         loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.pow(edge_to - recon_to, 2)), 1))
#         loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.pow(edge_from - recon_from, 2)), 1))
#         # without attention weights
#         # loss1 = torch.mean(torch.mean(torch.pow(edge_to - recon_to, 2), 1))
#         # loss2 = torch.mean(torch.mean(torch.pow(edge_from - recon_from, 2), 1))
#         return (loss1 + loss2)/2

# class ReconstructionLoss(nn.Module):
#     def __init__(self, beta=1.0, weight_loss1=0.5, weight_loss2=0.5, clip_val=None):
#         super(ReconstructionLoss, self).__init__()
#         self._beta = beta
#         self.weight_loss1 = weight_loss1
#         self.weight_loss2 = weight_loss2
#         self.clip_val = clip_val

#     def forward(self, edge_to, edge_from, recon_to, recon_from, a_to, a_from):
#         # Compute weights
#         weight_to = torch.pow((1+a_to), self._beta)
#         weight_from = torch.pow((1+a_from), self._beta)
        
#         # Optional: Clip weights
#         if self.clip_val is not None:
#             weight_to = torch.clamp(weight_to, max=self.clip_val)
#             weight_from = torch.clamp(weight_from, max=self.clip_val)
        
#         # Compute individual losses
#         loss1 = torch.mean(torch.mean(torch.multiply(weight_to, torch.pow(edge_to - recon_to, 2)), 1))
#         loss2 = torch.mean(torch.mean(torch.multiply(weight_from, torch.pow(edge_from - recon_from, 2)), 1))
        
#         # Return weighted sum of losses
#         return self.weight_loss1 * loss1 + self.weight_loss2 * loss2

class ReconstructionLoss(nn.Module):
    def __init__(self, beta=1.0,alpha=0.5):
        super(ReconstructionLoss, self).__init__()
        self._beta = beta
        self._alpha = alpha

    def forward(self, edge_to, edge_from, recon_to, recon_from, a_to, a_from):
        loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.pow(edge_to - recon_to, 2)), 1))
        loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.pow(edge_from - recon_from, 2)), 1))

        # l1_loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.abs(edge_to - recon_to)), 1))
        # l1_loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.abs(edge_from - recon_from)), 1))
        # l2_loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.pow(edge_to - recon_to, 2)), 1))
        # l2_loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.pow(edge_from - recon_from, 2)), 1))
        # loss1 = self._alpha * l1_loss1 + (1 - self._alpha) * l2_loss1
        # loss2 = self._alpha * l1_loss2 + (1 - self._alpha) * l2_loss2
    

        # without attention weights
        # loss1 = torch.mean(torch.mean(torch.pow(edge_to - recon_to, 2), 1))
        # loss2 = torch.mean(torch.mean(torch.pow(edge_from - recon_from, 2), 1))
        return (loss1 + loss2)/2


class ReconstructionPredEdgeLoss(nn.Module):
    def __init__(self, data_provider, iteration, beta=1.0,alpha=0.5):
        super(ReconstructionPredEdgeLoss, self).__init__()
        self._beta = beta
        self._alpha = alpha
        self.data_provider = data_provider
        self.iteration = iteration

    def forward(self, edge_to, edge_from, recon_to, recon_from, a_to, a_from):
        loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.pow(edge_to - recon_to, 2)), 1))
        loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.pow(edge_from - recon_from, 2)), 1))

        # Concatenate tensors
        concatenated_tensors = torch.cat([edge_to, edge_from, recon_to, recon_from], dim=0)
        # Convert to numpy and detach if necessary
        concatenated_numpy = concatenated_tensors.cpu().detach().numpy()
        # prediction
        concatenated_predictions = self.data_provider.get_pred(self.iteration, concatenated_numpy, 0)
        # Convert back to torch.Tensor
        concatenated_predictions_tensor = torch.Tensor(concatenated_predictions)

        # Split the predictions
        total_length = concatenated_predictions_tensor.shape[0]
        each_length = total_length // 4
        edge_pred_to = concatenated_predictions_tensor[:each_length]
        edge_pred_from = concatenated_predictions_tensor[each_length:2*each_length]
        recon_pred_to = concatenated_predictions_tensor[2*each_length:3*each_length]
        recon_pred_from = concatenated_predictions_tensor[3*each_length:]

        loss1_pred = torch.mean(torch.mean(torch.pow(edge_pred_to - recon_pred_to, 2), 1))
        loss2_pred = torch.mean(torch.mean(torch.pow(edge_pred_from - recon_pred_from, 2), 1))
    
        # without attention weights
        # loss1 = torch.mean(torch.mean(torch.pow(edge_to - recon_to, 2), 1))
        # loss2 = torch.mean(torch.mean(torch.pow(edge_from - recon_from, 2), 1))
        return (loss1 + loss2)/2 + (loss1_pred + loss2_pred) / 2

class ReconstructionPredLoss(nn.Module):
    def __init__(self, data_provider, epoch, beta=1.0,alpha=0.5):
        super(ReconstructionPredLoss, self).__init__()
        self._beta = beta
        self._alpha = alpha
        self.data_provider = data_provider
        self.epoch = epoch

    def forward(self, edge_to, edge_from, recon_to, recon_from, a_to, a_from):
        loss1 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_to), self._beta), torch.pow(edge_to - recon_to, 2)), 1))
        loss2 = torch.mean(torch.mean(torch.multiply(torch.pow((1+a_from), self._beta), torch.pow(edge_from - recon_from, 2)), 1))

        # calulate
        combined_edge = torch.cat((edge_from, edge_to), dim=0)  # 拼接 edge_from 和 edge_to
        combined_recon = torch.cat((recon_from, recon_to), dim=0)  # 拼接 recon_from 和 recon_to

        # org_pred = self.data_provider.get_pred(self.epoch, combined_edge.cpu().detach().numpy())
        # recon_pred = self.data_provider.get_pred(self.epoch, combined_recon.cpu().detach().numpy())

        # 计算拼接向量的重建损失
        point_loss = torch.mean(torch.pow(combined_edge - combined_recon, 2))
        # pred_loss = torch.mean(torch.pow(torch.Tensor(org_pred) - torch.Tensor(recon_pred), 2))

        # 结合边的损失和点的损失
        total_loss = point_loss + (loss1 + loss2)/2
    
        return total_loss

class SmoothnessLoss(nn.Module):
    def __init__(self, margin=0.0):
        super(SmoothnessLoss, self).__init__()
        self._margin = margin

    def forward(self, embedding, target, Coefficient):
        loss = torch.mean(Coefficient * torch.clamp(torch.norm(embedding-target, dim=1)-self._margin, min=0))
        return loss


class SingleVisLoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, lambd):
        super(SingleVisLoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.lambd = lambd

    def forward(self, edge_to, edge_from, a_to, a_from, outputs):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]

        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from)
        # recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from)
        umap_l = self.umap_loss(embedding_to, embedding_from)

        loss = umap_l + self.lambd * recon_l

        return umap_l, recon_l, loss

class HybridLoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, smooth_loss, lambd1, lambd2):
        super(HybridLoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.smooth_loss = smooth_loss
        self.lambd1 = lambd1
        self.lambd2 = lambd2

    def forward(self, edge_to, edge_from, a_to, a_from, embeded_to, coeff, outputs):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]

        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from)
        umap_l = self.umap_loss(embedding_to, embedding_from)
        smooth_l = self.smooth_loss(embedding_to, embeded_to, coeff)

        loss = umap_l + self.lambd1 * recon_l + self.lambd2 * smooth_l

        return umap_l, recon_l, smooth_l, loss


class TemporalLoss(nn.Module):
    def __init__(self, prev_w, device) -> None:
        super(TemporalLoss, self).__init__()
        self.prev_w = prev_w
        self.device = device
        for param_name in self.prev_w.keys():
            self.prev_w[param_name] = self.prev_w[param_name].to(device=self.device, dtype=torch.float32)

    def forward(self, curr_module):
        loss = torch.tensor(0., requires_grad=True).to(self.device)
        # c = 0
        for name, curr_param in curr_module.named_parameters():
            # c = c + 1
            prev_param = self.prev_w[name]
            # tf dvi: diff = tf.reduce_sum(tf.math.square(w_current[j] - w_prev[j]))
            loss = loss + torch.sum(torch.square(curr_param-prev_param))
            # loss = loss + torch.norm(curr_param-prev_param, 2)
        # in dvi paper, they dont have this normalization (optional)
        # loss = loss/c
        return loss


class DummyTemporalLoss(nn.Module):
    def __init__(self, device) -> None:
        super(DummyTemporalLoss, self).__init__()
        self.device = device

    def forward(self, curr_module):
        loss = torch.tensor(0., requires_grad=True).to(self.device)
        return loss
    

class PositionRecoverLoss(nn.Module):
    def __init__(self, device) -> None:
        super(PositionRecoverLoss, self).__init__()
        self.device = device
    def forward(self, position, recover_position):
        mse_loss = nn.MSELoss().to(self.device)
        loss = mse_loss(position, recover_position)
        return loss


class DVILoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, temporal_loss, lambd1, lambd2, device):
        super(DVILoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.temporal_loss = temporal_loss
        self.lambd1 = lambd1
        self.lambd2 = lambd2
        self.device = device

    def forward(self, edge_to, edge_from, a_to, a_from, curr_model, outputs):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]
        # TODO stop gradient edge_to_ng = edge_to.detach().clone()

        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from).to(self.device)
        umap_l = self.umap_loss(embedding_to, embedding_from).to(self.device)
        temporal_l = self.temporal_loss(curr_model).to(self.device)

        loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l

        return umap_l, self.lambd1 *recon_l, self.lambd2 *temporal_l, loss


class TrustALLoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, temporal_loss, lambd1, lambd2, device):
        super(TrustALLoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.temporal_loss = temporal_loss
        self.lambd1 = lambd1
        self.lambd2 = lambd2
        self.device = device

    def forward(self, edge_to, edge_from, a_to, a_from, curr_model, outputs, edge_to_pred, edge_from_pred):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]
        # TODO stop gradient edge_to_ng = edge_to.detach().clone()

        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from).to(self.device)
        umap_l = self.umap_loss(embedding_to, embedding_from,edge_to_pred, edge_from_pred).to(self.device)
        temporal_l = self.temporal_loss(curr_model).to(self.device)

        loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l

        return umap_l, self.lambd1 *recon_l, self.lambd2 *temporal_l, loss
        
       

class DVIALLoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, temporal_loss, lambd1, lambd2, lambd3, device):
        super(DVIALLoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.temporal_loss = temporal_loss
        self.lambd1 = lambd1
        self.lambd2 = lambd2
        self.lambd3 = lambd3
        self.device = device

        # self.cross_entropy_loss = nn.CrossEntropyLoss()
        self.mse_loss = nn.MSELoss()


    def forward(self, edge_to, edge_from, a_to, a_from, curr_model, outputs,data):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]
        # TODO stop gradient edge_to_ng = edge_to.detach().clone()
        # if self.lambd3 != 0:
        #     data = torch.tensor(data).to(device=self.device, dtype=torch.float32)
        #     recon_data = curr_model(data,data)['recon'][0]
        #     pred_loss = self.mse_loss(data, recon_data)
        # else:
        #     pred_loss = torch.Tensor(0)
            
        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from).to(self.device)
        umap_l = self.umap_loss(embedding_to, embedding_from).to(self.device)
        temporal_l = self.temporal_loss(curr_model).to(self.device)

        if self.lambd3 != 0:
            data = torch.tensor(data).to(device=self.device, dtype=torch.float32)
            recon_data = curr_model(data,data)['recon'][0]
            pred_loss = self.mse_loss(data, recon_data)
            loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l + self.lambd3 * pred_loss
            return umap_l, self.lambd1 *recon_l, self.lambd2 *temporal_l, loss, pred_loss
        else:
            loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l 
            pred_loss = torch.tensor(0.0).to(self.device)

        return umap_l, self.lambd1 *recon_l, self.lambd2 *temporal_l, loss, pred_loss 


        


class ActiveLearningLoss(nn.Module):
    def __init__(self, data_provider, iteration, device):
        super(ActiveLearningLoss, self).__init__()
        self.data_provider = data_provider
        self.iteration = iteration
        self.device = device

    def forward(self, curr_model,data):
         
        self.data = torch.tensor(data).to(device=self.device, dtype=torch.float32)
        recon_data = curr_model(self.data,self.data)['recon'][0]
        loss = self.cross_entropy_loss(self.data, recon_data)
        # normalized_loss = torch.sigmoid(loss)
        return  loss




class MINE(nn.Module):
    def __init__(self):
        super(MINE, self).__init__()
        # 在这里，MINE网络是一个MLP
        self.network = nn.Sequential(
            nn.Linear(2, 100),
            nn.ReLU(),
            nn.Linear(100, 1),
        )

    def forward(self, x, y):
        joint = torch.cat((x, y), dim=1)
        marginal = torch.cat((x, y[torch.randperm(x.size(0))]), dim=1)
        t_joint = self.network(joint)
        t_marginal = self.network(marginal)
        # 重新调整以避免exp(t)变为无穷大
        mi = torch.mean(t_joint) - torch.log(torch.mean(torch.exp(t_marginal)))
        return -mi  # 最大化mi <=> 最小化-mi


class TVILoss(nn.Module):
    def __init__(self, umap_loss, recon_loss, temporal_loss, MI_loss, lambd1, lambd2, lambd3, device):
        super(TVILoss, self).__init__()
        self.umap_loss = umap_loss
        self.recon_loss = recon_loss
        self.temporal_loss = temporal_loss
        self.MI_loss = MI_loss
        self.lambd1 = lambd1
        self.lambd2 = lambd2
        self.lambd3 = lambd3
        self.device = device

    def forward(self, edge_to, edge_from, a_to, a_from, curr_model, outputs):
        embedding_to, embedding_from = outputs["umap"]
        recon_to, recon_from = outputs["recon"]
        recon_l = self.recon_loss(edge_to, edge_from, recon_to, recon_from, a_to, a_from).to(self.device)
        umap_l = self.umap_loss(embedding_to, embedding_from).to(self.device)
        temporal_l = self.temporal_loss(curr_model).to(self.device)
         # 计算嵌入和边之间的互信息
        # MI_l = self.MI_loss(embedding_to, embedding_from, edge_to, edge_from).to(self.device)
        # Calculate mutual information between embedding and edge separately
        MI_l_embedding = self.MI_loss(embedding_to, embedding_from).to(self.device)
        MI_l_edge = self.MI_loss(edge_to, edge_from).to(self.device)
        # Assuming you want to give them equal weight, but you can adjust it as you need
        MI_l = (MI_l_embedding + MI_l_edge) / 2
        loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l + self.lambd3 * MI_l

        return umap_l, self.lambd1 * recon_l, self.lambd2 * temporal_l, loss

# class DVILoss(nn.Module):
#     def __init__(self, umap_loss, recon_loss, temporal_loss, lambd1, lambd2, device):
#         super(DVILoss, self).__init__()
#         self.umap_loss = umap_loss
#         self.recon_loss = recon_loss
#         self.temporal_loss = temporal_loss
#         self.lambd1 = lambd1
#         self.lambd2 = lambd2
#         self.device = device

#     def forward(self, edge_to, edge_from, a_to, a_from, curr_model, outputs):
#         embedding_to, embedding_from = outputs["umap"]
#         recon_to, recon_from = outputs["recon"]

#         # Create new tensors which do not require gradients
#         edge_to_ng = edge_to.detach()
#         edge_from_ng = edge_from.detach()

#         # Calculate loss with these new tensors
#         recon_l = self.recon_loss(edge_to_ng, edge_from_ng, recon_to, recon_from, a_to, a_from).to(self.device)
#         umap_l = self.umap_loss(embedding_to, embedding_from).to(self.device)
#         temporal_l = self.temporal_loss(curr_model).to(self.device)

#         loss = umap_l + self.lambd1 * recon_l + self.lambd2 * temporal_l

#         return umap_l, self.lambd1 *recon_l, self.lambd2 *temporal_l, loss


