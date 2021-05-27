#!/bin/bash

git -C bergamot-translator pull || git clone git@github.com:jerinphilip/bergamot-translator.git
git -C bergamot-translator fetch -a
git -C bergamot-translator checkout workflow-gen-exps
python3 examples/bergamot-translator/main.py > bergamot-translator/.github/workflows/native.yml

(cd bergamot-translator &&
        git add .github/workflows/native.yml &&
        git commit -m "Updating native.yml" &&
        git push origin workflow-gen-exps)
