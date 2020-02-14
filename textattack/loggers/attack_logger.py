import numpy as np
import torch

from textattack.attack_results import AttackResult, FailedAttackResult, SkippedAttackResult

from . import CSVLogger, FileLogger, VisdomLogger

class AttackLogger:
    def __init__(self):
        """ Logs the results of an attack to all attached loggers
        """
        self.loggers = []
        self.results = []
        self.max_words_changed = 0
        self.max_seq_len = 2**16

    def enable_stdout(self):
        self.loggers.append(FileLogger(stdout=True))

    def enable_visdom(self):
        self.loggers.append(VisdomLogger())

    def add_output_file(self, filename):
        self.loggers.append(FileLogger(filename=filename))

    def add_output_csv(self, filename, plain):
        self.loggers.append(CSVLogger(filename=filename, plain=plain))

    def log_result(self, result):
        self.results.append(result)
        for logger in self.loggers:
            logger.log_attack_result(result)
    
    def log_results(self, results):
        for result in results:
            self.log_result(result)
        self.log_summary()

    def _log_rows(self, rows, title, window_id):
        for logger in self.loggers:
            logger.log_rows(rows, title, window_id)

    def log_sep(self):
        for logger in self.loggers:
            logger.log_sep()

    def flush(self):
        for logger in self.loggers:
            logger.flush()

    def log_attack_details(self, attack_name, model_name):
        attack_detail_rows = [
            ['Attack algorithm:', attack_name],
            ['Model:', model_name],
        ]
        self._log_rows(attack_detail_rows, 'Attack Details', 'attack_details')
    
    def log_summary(self):
        total_attacks = len(self.results)
        if total_attacks == 0:
            return
        # Count things about attacks.
        all_num_words = np.zeros(len(self.results))
        perturbed_word_percentages = np.zeros(len(self.results))
        num_words_changed_until_success =  np.zeros(self.max_seq_len)
        failed_attacks = 0
        skipped_attacks = 0
        successful_attacks = 0
        max_words_changed = None
        for i, result in enumerate(self.results):
            if isinstance(result, FailedAttackResult):
                failed_attacks += 1
            elif isinstance(result, SkippedAttackResult):
                skipped_attacks += 1
            else: 
                successful_attacks += 1
            num_words_changed =  len(result.original_text.all_words_diff(result.perturbed_text))
            num_words_changed_until_success[num_words_changed-1] += 1
            max_words_changed = max(max_words_changed or num_words_changed, num_words_changed)
            if num_words_changed > 0:
                perturbed_word_percentage = num_words_changed * 100.0 / len(result.original_text.words)
            else:
                perturbed_word_percentage = 0
            perturbed_word_percentages[i] = perturbed_word_percentage
            num_words_changed_until_success[i] = len(result.original_text.words)
            all_num_words[i] = len(result.original_text.words)
        
        # Original classifier success rate on these samples.
        original_accuracy = (total_attacks - skipped_attacks)  * 100.0 / (total_attacks) 
        original_accuracy = str(round(original_accuracy, 2)) + '%'
        
        # New classifier success rate on these samples.
        accuracy_under_attack = (failed_attacks) * 100.0 / (total_attacks)
        accuracy_under_attack = str(round(accuracy_under_attack, 2)) + '%'
        
        # Attack success rate.
        if successful_attacks + failed_attacks == 0:
            attack_success_rate = 0
        else:
            attack_success_rate = successful_attacks * 100.0 / (successful_attacks + failed_attacks) 
        attack_success_rate = str(round(attack_success_rate, 2)) + '%'
        
        perturbed_word_percentages = perturbed_word_percentages[perturbed_word_percentages > 0]
        average_perc_words_perturbed = perturbed_word_percentages.mean()
        average_perc_words_perturbed = str(round(average_perc_words_perturbed, 2)) + '%'
        
        average_num_words = all_num_words.mean()
        average_num_words = str(round(average_num_words, 2))
        
        summary_table_rows = [
            ['Number of successful attacks:', str(successful_attacks)],
            ['Number of failed attacks:', str(failed_attacks)],
            ['Number of skipped attacks:', str(skipped_attacks)],
            ['Original accuracy:', original_accuracy],
            ['Accuracy under attack:', accuracy_under_attack],
            ['Attack success rate:', attack_success_rate],
            ['Average perturbed word %:', average_perc_words_perturbed],
            ['Average num. words per input:', average_num_words],
        ]
        
        num_queries = np.array([r.num_queries for r in self.results])
        avg_num_queries = num_queries.mean()
        avg_num_queries = str(round(avg_num_queries, 2))
        summary_table_rows.append(['Avg num queries:', avg_num_queries])
        self._log_rows(summary_table_rows, 'Attack Results', 'attack_results_summary')
        # Show histogram of words changed.
        numbins = max(self.max_words_changed, 10)
        for logger in self.loggers:
            logger.log_hist(num_words_changed_until_success[:numbins],
                numbins=numbins, title='Num Words Perturbed', window_id='num_words_perturbed')
