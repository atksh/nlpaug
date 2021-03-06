import string
import re

from nlpaug.util import Method
from nlpaug import Augmenter
from nlpaug.util import WarningException, WarningName, WarningCode, WarningMessage


class WordAugmenter(Augmenter):
    TOKENIZER_REGEX = re.compile(r'(\W)')

    def __init__(self, action, name='Word_Aug', aug_min=1, aug_max=10, aug_p=0.3, stopwords=None,
                 tokenizer=None, reverse_tokenizer=None, device='cpu', verbose=0, stopwords_regex=None,
                 include_detail=False):
        super().__init__(
            name=name, method=Method.WORD, action=action, aug_min=aug_min, aug_max=aug_max, device=device,
            verbose=verbose, include_detail=include_detail)
        self.aug_p = aug_p
        self.tokenizer = tokenizer or self._tokenizer
        self.reverse_tokenizer = reverse_tokenizer or self._reverse_tokenizer
        self.stopwords = stopwords
        self.stopwords_regex = re.compile(stopwords_regex) if stopwords_regex is not None else stopwords_regex

    @classmethod
    def _tokenizer(cls, text):
        tokens = cls.TOKENIZER_REGEX.split(text)
        return [t for t in tokens if len(t.strip()) > 0]

    @classmethod
    def _reverse_tokenizer(cls, tokens):
        return ' '.join(tokens)

    @classmethod
    def clean(cls, data):
        return data.strip()

    def skip_aug(self, token_idxes, tokens):
        return token_idxes

    def pre_skip_aug(self, tokens, tuple_idx=None):
        results = []
        for token_idx, token in enumerate(tokens):
            if tuple_idx is not None:
                _token = token[tuple_idx]
            else:
                _token = token
            # skip punctuation
            if _token in string.punctuation:
                continue
            """
                TODO: cannot skip word that were split by tokenizer
            """
            # skip stopwords by list
            if self.stopwords is not None and _token in self.stopwords:
                continue

            # skip stopwords by regex
            # https://github.com/makcedward/nlpaug/issues/81
            if self.stopwords_regex is not None and (
                    self.stopwords_regex.match(_token) or self.stopwords_regex.match(' '+_token+' ') or
                    self.stopwords_regex.match(' '+_token) or self.stopwords_regex.match(_token+' ')):
                continue

            results.append(token_idx)

        return results

    @classmethod
    def is_duplicate(cls, dataset, data):
        for d in dataset:
            if d == data:
                return True
        return False

    def align_capitalization(self, src_token, dest_token):
        if self.get_word_case(src_token) == 'capitalize' and self.get_word_case(dest_token) == 'lower':
            return dest_token.capitalize()
        return dest_token

    def _get_aug_idxes(self, tokens):
        aug_cnt = self.generate_aug_cnt(len(tokens))
        word_idxes = self.pre_skip_aug(tokens)
        word_idxes = self.skip_aug(word_idxes, tokens)
        if len(word_idxes) == 0:
            if self.verbose > 0:
                exception = WarningException(name=WarningName.OUT_OF_VOCABULARY,
                                             code=WarningCode.WARNING_CODE_002, msg=WarningMessage.NO_WORD)
                exception.output()
            return []
        if len(word_idxes) < aug_cnt:
            aug_cnt = len(word_idxes)
        aug_idexes = self.sample(word_idxes, aug_cnt)
        return aug_idexes

    def _get_random_aug_idxes(self, tokens):
        aug_cnt = self.generate_aug_cnt(len(tokens))
        word_idxes = self.pre_skip_aug(tokens)
        if len(word_idxes) < aug_cnt:
            aug_cnt = len(word_idxes)

        aug_idxes = self.sample(word_idxes, aug_cnt)

        return aug_idxes

    def _get_aug_range_idxes(self, tokens):
        aug_cnt = self.generate_aug_cnt(len(tokens))
        direction = self.sample([-1, 1], 1)[0]

        if direction > 0:
            # right
            word_idxes = [i for i, _ in enumerate(tokens[:-aug_cnt+1])]
        else:
            # left
            word_idxes = [i for i, _ in enumerate(tokens[aug_cnt-1:])]

        start_aug_idx = self.sample(word_idxes, 1)[0]
        aug_idxes = [start_aug_idx + _*direction for _ in range(aug_cnt)]

        return aug_idxes

    @classmethod
    def get_word_case(cls, word):
        if len(word) == 0:
            return 'empty'

        if len(word) == 1 and word.isupper():
            return 'capitalize'

        if word.isupper():
            return 'upper'
        elif word.islower():
            return 'lower'
        else:
            for i, c in enumerate(word):
                if i == 0:  # do not check first character
                    continue
                if c.isupper():
                    return 'mixed'

            if word[0].isupper():
                return 'capitalize'
            return 'unknown'
