import math
import re
import sys
import json

# Replace words that occur fewer than 5 times in file with rare symbols
def rarify(filename):
    # Iterate through file and replace occurances of words in final rare dictionary with '_RARE_' symbol
    temp = abound(filename)
    abundant = temp[0]
    trees = temp[1]
    file = open(filename, 'w')
    # Iterate through tree list
    for i in range(0, len(trees)):
        tree = trees[i]
        rarify_recurse(tree, abundant) # Recursively parse each tree to replace rare terminal symbols
        file.write(json.dumps(tree) + '\n') # Convert tree back to JSON and write to file
    file.close()

# Find "abundant" (occur 5 or more times) in training file
# Returns abundant set and list of trees in training file in order
def abound(filename):
    abundant = set() # Keep track of words that occur 5 or more times
    rare = {} # Keep track of words that occur fewer than 5 times with current count
    file = open(filename, 'r')
    trees = {} # Store all trees in file for re-write
    i = 0
    # Iterate through file and populate abundant and rare
    for line in file: # Parse file by line
        tree = json.loads(line) # Convert tree from JSON
        if len(tree) > 0:
            temp = abound_recurse(tree, abundant, rare) # Recursively parse each tree for terminal symbols
            abundant = temp[0] # Update abundant
            rare = temp[1] # Update rare
        trees[i] = tree # Store tree in tree list
        i += 1
    file.close()
    return (abundant, trees)

# Recursive step for "rarify"
def rarify_recurse(tree, abundant):
    # Base case: trees of length 2 (unary rules) end in a terminal symbol
    if len(tree) == 2:
        word = tree[1]
        # Identify and replace rare terminal symbols
        if word not in abundant:
            tree[1] = '_RARE_'
        return tree
    # Recursive case: trees of length 3 (binary rules) are subdivided into left and right trees for parsing
    elif len(tree) == 3:
        rarify_recurse(tree[1], abundant)
        rarify_recurse(tree[2], abundant)

# Recursive step for "abound"
def abound_recurse(tree, abundant, rare):
    # Base case: trees of length 2 (unary rules) end in a terminal symbol
    if len(tree) == 2:
        word = tree[1]
        # If this is the sixth or greater occurrence of word, do nothing
        if word not in abundant:
            # If first occurrence of word, add to "rare" 
            if word not in rare:
                rare[word] = 1
            else:
                # If fifth occurrence of word, remove from "rare" and add to "abundant"
                if rare[word] == 4:
                    abundant.add(word)
                    rare.pop(word)
                # Otherwise, increment count of word in "rare"
                else:
                    rare[word] += 1
        return [abundant, rare]
    # Recursive case: trees of length 3 (binary rules) are subdivided into left and right trees for parsing
    elif len(tree) == 3:
        temp = abound_recurse(tree[1], abundant, rare)
        return abound_recurse(tree[2], temp[0], temp[1])

# Calculate maximum likelihood estimates of all rules from hashes of counts
def q_rules(binary, unary, nonterminals):
    q_hash = {}
    for rule in binary:
        rule_count = float(binary[rule])
        start = (str.split(rule))[0]
        start_count = float(nonterminals[start])
        q_hash[rule] = rule_count/start_count
    for rule in unary:
        rule_count = float(unary[rule])
        start = (str.split(rule))[0]
        start_count = float(nonterminals[start])
        q_hash[rule] = rule_count/start_count
    return q_hash

# Returns dictionaries of counts provided in file for future O(1) access
def count_hashes(filename):
    file = open(filename, 'r')
    binary_counts = {}
    unary_counts = {}
    start_counts = {}
    abundant = set()
    for line in file: # Parse file by line
        parsed = str.split(line) # Parse line by whitespace
        if len(parsed) > 0:
            if parsed[1] == 'UNARYRULE': # Unary rules
                rule = parsed[2] + ' ' + parsed[3]
                unary_counts[rule] = int(parsed[0])
                # Simultaneously generate set of abundant (unrare) words from training file
                if parsed[3] not in abundant:
                    abundant.add(parsed[3])
            elif parsed[1] == 'BINARYRULE': # Binary rules
                rule = parsed[2] + ' ' + parsed[3] + ' ' + parsed[4]
                binary_counts[rule] = int(parsed[0])
            else: # Terminals
                start_counts[parsed[2]] = int(parsed[0])
    file.close()
    return (unary_counts, binary_counts, start_counts, abundant)

# CKY Algorithm
# Returns maximum probability parse tree of each sentence in file specified by filename
# Writes results to 'cky_predictions.txt'
def cky(filename, counts_filename, predictions_filename):
    # Generate counts hashes from file specified by counts_filename
    counts = count_hashes(counts_filename)
    unary_counts = counts[0]
    binary_counts = counts[1]
    start_counts = counts[2]
    abundant = counts[3]
    q_hash = q_rules(binary_counts, unary_counts, start_counts)
    # Genereate sets of rules and non-terminals from counts hashes
    non_terminals = start_counts.keys()
    unary_rules = unary_counts.keys()
    binary_rules = binary_counts.keys()
    # Open file to parse for reading and new predicitions file to write parse results
    file = open(filename, 'r')
    predictions = open(predictions_filename, 'w')
    for line in file: # Parse file by line
        sentence = str.split(line) # Parse line by space
        n = len(sentence)
        if n > 0:
            pies = {}
            # Initialization
            for i in range(1, n+1):
                for x in non_terminals:
                    if sentence[i-1] in abundant: # Abundant (unrare) terminal word
                        rule = x + ' ' + sentence[i-1]
                    else: # Rare terminal word
                        rule = x + ' _RARE_'
                    if rule in unary_rules: # Unary rules in grammar
                        pies[(i,i,x)] = (q_hash[rule], (sentence[i-1],i))
                    else: # Unary rules not in grammar
                        pies[(i,i,x)] = (0, (sentence[i-1],i))
            # Algorithm
            # Vary over all possible divisions into left and right subtrees
            for l in range(1, n):
                for i in range(1, n-l+1):
                    j = i + l
                    # Vary over all possible start non-terminal symbols
                    for x in non_terminals:
                        max_prob = 0.0
                        # Find maximum probability over all possible binary rules with specified start symbol
                        for rule in binary_rules:
                            r = str.split(rule)
                            if r[0] == x:
                                q = q_hash[rule]
                                # Find maximum probability over all possible divisions into left and right subtrees
                                for s in range(i, j):
                                    prob = q * pies[(i,s,r[1])][0] * pies[(s+1,j,r[2])][0]
                                    if prob >= max_prob:
                                        max_prob = prob
                                        prob_term = ((r[1],s), (r[2],s+1))
                        pies[(i,j,x)] = (max_prob, prob_term)
            s = 'S'
            if pies[(1, n, 'S')][0] == 0:
                max_prob = -1.0
                for x in non_terminals:
                    if pies[(1, n, x)][0] > max_prob:
                        s = x
                        max_prob = pies[(1, n, x)][0]
            tree = gen_tree(1, n, s, pies, sentence) # Use backpointers to generate maximum probability parse tree
            predictions.write(json.dumps(tree)) # Convert tree to JSON and write to file
        predictions.write('\n')
    file.close()
    predictions.close()

# Recursively generate parse tree from pi values
def gen_tree(first, last, start, pies, sentence):
    # Base case: unary rule
    if first == last:
        return [start, sentence[first-1]]
    # Recursive case: binary rule
    else:
        left = pies[(first,last,start)][1][0]
        right = pies[(first,last,start)][1][1]
        return [start, gen_tree(first, left[1], left[0], pies, sentence), gen_tree(right[1], last, right[0], pies, sentence)]

def main(args):
    if args[1] == 'rarify':
        rarify(args[2])
    if args[1] == 'cky':
        cky(args[2], args[3], args[4])

if __name__ == "__main__":
    main(sys.argv)