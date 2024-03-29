# from multiprocessing import Pool, cpu_count
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag

import networkx as nx
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('wordnet')



# import pygraphviz

def stopwords():
    with open('stopwords.txt', 'r') as f:
        return set(l[:-1] for l in f.readlines())


def text2sents(text):
    lemmatizer = WordNetLemmatizer()
    stops = stopwords()
    sents = sent_tokenize(text)
    lss = []
    for sent in sents:
        ws = word_tokenize(sent)
        wts = pos_tag(ws)

        ls = []
        for w, t in wts:
            lw = w.lower()
            if not lw.isalpha(): continue
            if lw in stops: continue
            lemma = lemmatizer.lemmatize(w)
            if lemma in stops: continue
            tag = t[0]
            ls.append(W(lemma, w, tag))
        if not ls: continue
        lss.append((ls, sent))
    return lss


class W:
    def __init__(self, lemma, word, tag):
        self.lemma = lemma
        self.word = word
        self.tag = tag

    def __repr__(self):
        return f"W('{self.lemma}','{self.word}','{self.tag}')"


def add_compounds(g, sid, ls):
    cs = 0
    m = len(ls)
    added = set()
    for i, w in enumerate(ls):
        if i < m - 2 and w.tag in 'RJ' and ls[i + 1].tag in 'J' and ls[i + 2].tag in 'N':
            t = " ".join([w.word, ls[i + 1].word, ls[i + 2].word])
            for x in ls[i:i + 3]:
                f = x.lemma
                g.add_edge(f, t)
                added.add(i)
                added.add(i + 1)
                added.add(i + 2)
                g.add_edge(sid, t)
        elif i < m - 1 and i not in added and (i + 1) not in added and \
            w.tag in 'NJ' and ls[i + 1].tag in 'N':
            for x in ls[i:i + 2]:
                f = x.lemma
                t = " ".join([w.word, ls[i + 1].word])
                g.add_edge(f, t)
                g.add_edge(sid, t)


def sents2graph(lss):
    g = nx.DiGraph()
    g.add_edge(0, len(lss) - 1)  # first ot last sent
    for sent_id, (ls, _) in enumerate(lss):
        if sent_id > 0:  # from sent to sent before it
            g.add_edge(sent_id, sent_id - 1)
        g.add_edge(ls[0].lemma, sent_id)  # from 1-st word to sent id
        g.add_edge(sent_id, ls[-1].lemma)  # from sent id to last word
        # g.add_edge(ls[0], ls[-1]) # from first word to last word
        for j, w in enumerate(ls):
            if j > 0: g.add_edge(w.lemma, ls[j - 1].lemma)
        add_compounds(g, sent_id, ls)
    return g


def textstar(g, ranker, sumsize, kwsize, trim):
    assert sumsize > 0 or kwsize > 0
    final_sids, final_kwds = None, None
    while True:

        unsorted_ranks = ranker(g)
        ranks = sorted(unsorted_ranks.items(), reverse=True, key=lambda x: x[1])

        sids = [sid for (sid, _) in ranks if isinstance(sid, int)]
        kwds = [w for (w, _) in ranks if isinstance(w, str)]

        print('=> S_NODES:', len(sids), 'W_NODES', len(kwds))
        s_done = len(sids) <= sumsize
        w_done = len(kwds) <= kwsize
        if s_done and not final_sids:
            final_sids = sids
        if w_done and not final_kwds:
            final_kwds = kwds

        total = len(ranks)
        split = trim * total // 100
        # print(ranks)
        weak_nodes = [n for (n, _) in ranks[split:]]
        weakest = weak_nodes[-1]
        weakest_rank = unsorted_ranks[weakest]
        for n in weak_nodes:
            g.remove_node(n)
        for n, r in ranks[0:split]:
            if r <= weakest_rank:
                g.remove_node(n)

        if s_done or w_done: 
            if not s_done:
                final_sids = sids[:sumsize]
            if not w_done:
                final_kwds = kwds[:kwsize]   
            break

    return final_sids, final_kwds


def process_text(text, ranker=nx.pagerank, sumsize=6, kwsize=6, trim=80, show=False):
    lss = text2sents(text)
    print("#SENT:", len(lss))

    g = sents2graph(lss)
    print(g)

    if show and g.number_of_edges() < 600:
        nx.nx_agraph.write_dot(g, 'pic.gv')

    # for f,t in g.edges(): print(t,'<-',f)
    final_sids, final_kwds = textstar(g, ranker, sumsize, kwsize, trim)

    sids = final_sids[0:sumsize]
    sids = sorted(sids)
    print("SIDS:", sids)
    all_sents = [sent for (_, sent) in lss]
    sents = [(i, all_sents[i]) for i in sids]

    kwds = final_kwds[0:kwsize]

    return sents, kwds


def summarize(fname, ranker=nx.pagerank, show=False):
    with open(fname + ".txt", 'r') as f:
        text = f.read()
    sents, kwds = process_text(
        text=text,
        ranker=ranker,
        show=show)
    return sents, kwds


def test_textstar():
    sents, kwds = summarize('../texts/english', show=True)

    print('SUMMARY:')
    for sent in sents:
        print(*sent)
    print('\nKEYWORDS:')
    print("; ".join(kwds) + ".")


if __name__ == "__main__":
    # print(stopwords())
    test_textstar()
