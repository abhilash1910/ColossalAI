# MIT License

# Copyright (c) 2022 Ming Zhong

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
from typing import Dict

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import tqdm


def add_question(dimension, output, src=None, ref=None, context=None, task=None):
    """
        Add questions to generate input in Bool-QA format for UniEval.

        dimension: specific dimension to be evaluated
        src: source input for different NLG tasks. For example, source document for summarization
             and dialogue history for dialogue response generation.
        output: output text generated by the models
        ref: human-annotated groundtruth
        context: the context needed to evaluate several specific dimension. For example,
                 additional factual information when evaluating engagingness and groundedness in dialogues.
    """

    input_with_question = []
    for i in range(len(output)):
        # For summarization
        if task == 'summarization':
            if dimension == 'fluency':
                cur_input = 'question: Is this a fluent paragraph? </s> paragraph: ' + output[i]
            elif dimension == 'coherence':
                cur_input = 'question: Is this a coherent summary to the document? </s> summary: ' + output[
                    i] + ' </s> document: ' + src[i]
            elif dimension == 'consistency':
                cur_input = 'question: Is this claim consistent with the document? </s> claim: ' + output[
                    i] + ' </s> document: ' + src[i]
            elif dimension == 'relevance':
                cur_input = 'question: Is this summary relevant to the reference? </s> summary: ' + output[
                    i] + ' </s> reference: ' + ref[i]
            else:
                raise NotImplementedError(
                    'The input format for this dimension is still undefined. Please customize it first.')
        # For dialogues
        elif task == 'dialogue':
            if dimension == 'naturalness':
                cur_input = 'question: Is this a natural response in the dialogue? </s> response: ' + output[i]
            elif dimension == 'coherence':
                cur_input = 'question: Is this a coherent response given the dialogue history? </s> response: '\
                            + output[i] + ' </s> dialogue history: ' + src[i]
            elif dimension == 'engagingness':
                cur_input = 'question: Is this an engaging and informative response according to the dialogue history and fact? </s> response: '\
                            + output[i] + ' </s> dialogue history: ' + src[i] + ' </s> fact: ' + context[i]
            elif dimension == 'groundedness':
                cur_input = 'question: Is this response consistent with knowledge in the fact? </s> response: '\
                            + output[i] + ' </s> fact: ' + context[i]
            elif dimension == 'understandability':
                cur_input = 'question: Is this an understandable response in the dialogue? </s> response: ' + output[i]
            else:
                raise NotImplementedError(
                    'The input format for this dimension is still undefined. Please customize it first.')
        # For data-to-text
        elif task == 'data2text':
            if dimension == 'naturalness':
                cur_input = 'question: Is this a fluent utterance? </s> utterance: ' + output[i]
            elif dimension == 'informativeness':
                cur_input = 'question: Is this sentence informative according to the reference? </s> sentence: '\
                            + output[i] + ' </s> reference: ' + ref[i]
            else:
                raise NotImplementedError(
                    'The input format for this dimension is still undefined. Please customize it first.')
        # For factual consistency detection
        elif task == 'fact':
            if dimension == 'consistency':
                cur_input = 'question: Is this claim consistent with the document? </s> claim: ' + output[
                    i] + ' </s> document: ' + src[i]
            else:
                raise NotImplementedError('No other dimensions for the factual consistency detection task.')
        # For new customized tasks
        else:
            raise NotImplementedError('Other tasks are not implemented, please customize specific tasks here.')
        input_with_question.append(cur_input)
    return input_with_question


def convert_data_to_unieval_format(output_list, src_list=None, ref_list=None):
    """
        Convert the data into the unieval's format.

        output_list: a list of model output

        src_list: source input for different NLG tasks. For example, source document for summarization
                  and dialogue history for dialogue response generation
        ref_list: human-annotated groundtruth
    """
    json_data = []
    for i in range(len(output_list)):
        cur = {}
        cur['system_output'] = output_list[i]
        if src_list is not None:
            cur['source'] = src_list[i]
        if ref_list is not None:
            cur['reference'] = ref_list[i]
        cur['context'] = ""
        json_data.append(cur)
    return json_data


def calculate_average_score(scores):
    """
        Calculate average scores for different metrics

        scores: a list of scores for different metrics for each answer

    """
    metrics = {metric: 0 for metric in scores[0]}

    for score in scores:
        for metric in score:
            metrics[metric] += score[metric]

    for metric in metrics:
        metrics[metric] /= len(scores)

    return metrics


def save_unieval_results(model_name: str, unieval_metric_stats: Dict[str, Dict], save_path: str) -> None:
    """
    Save UniEval evaluation results of different categories for one model.

    """

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    unieval_metric_stats_per_category = {}
    for task, category_stat in unieval_metric_stats.items():
        for category, metric_stat in category_stat.items():
            if unieval_metric_stats_per_category.get(category, None) is None:
                unieval_metric_stats_per_category[category] = {}
            for metric, score in metric_stat.items():
                unieval_metric_stats_per_category[category][f"{metric}-{task}"] = score

    automatic_df = pd.DataFrame(unieval_metric_stats_per_category)
    automatic_df.to_csv(os.path.join(save_path, f"{model_name}_results.csv"), index=True)


def read_unieval_results(results_path: str, file_name: str) -> Dict[str, Dict]:
    """
    Read a csv file and return a dictionary which stores scores per metric.

    """

    results = pd.read_csv(os.path.join(results_path, file_name), index_col=0)

    results_dict = {metric: {} for metric in list(results.index)}
    for i, metric in enumerate(results_dict.keys()):
        for j, category in enumerate(list(results.columns)):
            if pd.isnull(results.iloc[i][j]):
                continue
            results_dict[metric][category] = results.iloc[i][j]

    return results_dict


def analyze_unieval_results(results_path: str, save_path: str) -> None:
    """
    Analyze and visualize all csv files in the given folder.

    """

    if not os.path.exists(results_path):
        raise Exception(f'The given directory "{results_path}" doesn\'t exist! No results found!')

    all_statistics = {}

    for file_name in os.listdir(results_path):
        if file_name.endswith("_results.csv"):
            model_name = file_name.split("_results.csv")[0]
            all_statistics[model_name] = read_unieval_results(results_path, file_name)

    if len(list(all_statistics.keys())) == 0:
        raise Exception(f'There are no csv files in the given directory "{results_path}"!')

    frame_all = {"model": [], "category": [], "metric": [], "score": []}
    frame_per_metric = {}
    for model_name, model_statistics in all_statistics.items():
        for metric, metric_statistics in model_statistics.items():
            if frame_per_metric.get(metric) is None:
                frame_per_metric[metric] = {"model": [], "category": [], "score": []}

            for category, category_score in metric_statistics.items():
                frame_all["model"].append(model_name)
                frame_all["category"].append(category)
                frame_all["metric"].append(metric)
                frame_all["score"].append(category_score)

                frame_per_metric[metric]["model"].append(model_name)
                frame_per_metric[metric]["category"].append(category)
                frame_per_metric[metric]["score"].append(category_score)

    if not os.path.exists(save_path):
        os.makedirs(save_path)

    frame_all = pd.DataFrame(frame_all)
    frame_all.to_csv(os.path.join(save_path, "unieval_statistics.csv"))

    for metric in tqdm.tqdm(
            frame_per_metric.keys(),
            desc=f"UniEval metrics: ",
            total=len(frame_per_metric.keys()),
    ):
        data = pd.DataFrame(frame_per_metric[metric])

        sns.set()
        fig = plt.figure(figsize=(16, 10))

        fig = sns.barplot(x="category", y="score", hue="model", data=data, dodge=True)
        fig.set_title(
            f"Comparison between Different Models for Metric {metric.split('-')[0].title()} in Task {metric.split('-')[1].title()}"
        )
        plt.xlabel("Evaluation Category")
        plt.ylabel("Score")

        figure = fig.get_figure()
        figure.savefig(os.path.join(save_path, f"{metric}.png"), dpi=400)

        plt.close()
