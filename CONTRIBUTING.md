# Contributing

First of all, thank you for your interest in contributing to Xiamon!

Xiamon is still in its early development state and there are some exciting features in the pipeline. But as this is a spare time project, cuts had to be made somewhere. So stuff like linting, formatting, etc. is not set up yet, but will follow soon(TM).

## **The golden rule**

Communication is key! If you have some ideas for this project you want to implement, I really appreciate that. Let us talk about it before the coding starts (you can find contact information in the [README.md](README.md)), so no bad surprises happen when the pull request is created.

For stuff with low effort, directly creating a pull request is fine.

## **Branching model**

The `main` branch is stable and always contains the latest release.

The `release` branch represents the current state of the next release. It should be working, but consider the software there as in the "alpha" state.

`feature` branches contain stuff under development, so please use one for contributing.

`feature` branches are merged into the `release` branch. The `release` branch is merged into the `master` once the release is ready.

Please use rebase instead of [foxtrott merges](https://blog.developer.atlassian.com/stop-foxtrots-now/).

## **How to contribute**

1. Fork the repository
2. Create your `feature` branch from the `release` branch
3. Push your changes to the branch on your forked repository
4. Create a pull request towards `main` of this repository

In case of an urgent bugfix, I will then create a second `release` branch, cherrypick all the necessary stuff and release a minor release.

## **Commit messages**

Please keep the commit message short but descriptive. There are no further rules about commit messages here.