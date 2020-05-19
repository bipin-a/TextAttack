""" Abstract classes represent constraints on text adversarial examples. 
"""

from textattack.shared.utils import default_class_repr
from textattack.constraints import PreTransformationConstraint
from textattack.shared.validators import transformation_consists_of_word_swaps
import nltk

class StopwordModification(PreTransformationConstraint):
    """ 
    A constraint disallowing the modification of stopwords
    """
  
    def __init__(self, stopwords=None):
        if stopwords is not None:
            self.stopwords = set(stopwords)
        else:
            self.stopwords = set(nltk.corpus.stopwords.words('english'))

    def _get_modifiable_indices(self, tokenized_text):
        """ Returns the word indices in x which are able to be deleted """
        non_stopword_indices = set()
        for i, word in enumerate(tokenized_text.words):
            if word not in self.stopwords:
                non_stopword_indices.add(i)
        return non_stopword_indices

    def check_compatibility(self, transformation):
        """ 
        The stopword constraint only is concerned with word swaps since, paraphrasing phrases
        containing stopwords is OK.
        Args:
            transformation: The transformation to check compatibility with.
        """
        return transformation_consists_of_word_swaps(transformation)
