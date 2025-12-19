# Prompt Evolution Lab
## Towards Systematic Prompt Optimisation for Real Tasks using Evolutionary Algorithms

### Gauransh Kumar & Vennila Sooben
IFT 6076

---

This folder contains the submission for the IFT 6076 course. It includes the `Optimisation ESM2.cforge` and `Optimisation MPM.cforge` files, which contain the final optimised prompts for the ESM and MPM datasets, respectively. These files can be loaded in the ChainForge application to view the optimised prompts; however, the application **must be built from this branch** for them to work correctly.

### Installation
To install ChainForge from this branch, use the bash script `local_build.sh` located in the root directory of the repository. Run it to install ChainForge from this branch on Linux or macOS.
Existing installation methods for ChainForge should also work, provided that the build is sourced from this branch.

**Contact:** For any questions or issues, please contact [gauransh.kumar@umontreal.ca](mailto:gauransh.kumar@umontreal.ca).

---

### Extras
There is another experimental branch in this repository: [evo-optimiser-prompt-integrated](https://github.com/gauranshkumar/ChainForge/tree/evo-optimiser-prompt-integrated).
This branch implements a more integrated version of the prompt optimiser. It is not yet ready for production use but is available for reference and can be built using the same bash script. Please note that the submitted `.cforge` files are **not compatible** with the experimental branch.


