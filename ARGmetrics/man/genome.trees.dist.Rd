% Generated by roxygen2: do not edit by hand
% Please edit documentation in R/genome_trees_dist.r
\name{genome.trees.dist}
\alias{genome.trees.dist}
\title{Use tree metrics to compare two inferred ancestries (ARGs) over a genomic region}
\usage{
genome.trees.dist(treeseq.a = NA, treeseq.b = NA,
  output.full.table = FALSE, acceptable.length.diff.pct = 0.1,
  variant.positions = NULL, randomly.resolve.a = FALSE,
  randomly.resolve.b = FALSE, force.rooted = TRUE)
}
\arguments{
\item{treeseq.a}{The first multiPhylo object, or a path to a .nex file}

\item{treeseq.b}{The second multiPhylo object, or a path to a .nex file}

\item{output.full.table}{Output tree metrics for each overlapping region, rather than simply a weighted summary.}

\item{acceptable.length.diff.pct}{How much difference in sequence length is allowed between the 2 trees? (Default: 0.1 percent)}

\item{variant.positions}{A vector of genome positions of each variant. If given the metric will be 
calculated for each variant site and averaged over all sites, rather than averaged over every point on the genome}

\item{randomly.resolve.a}{Some distance metrics only operate on binary trees. Set this to TRUE to 
force trees in treeseq.a to be binary by randomly resolving polytomies where necessary, using the
multi2di routine in the 'ape' library. If this is a number, it is additionally used as an RNG seed.}

\item{randomly.resolve.b}{Some distance metrics only operate on binary trees. Set this to TRUE to 
force trees in treeseq.b to be binary by randomly resolving polytomies where necessary, using the
multi2di routine in the 'ape' library. If this is a number, it is additionally used as an RNG seed.}

\item{force.rooted}{Force input trees to be treated as rooted, even if there is a polytomy at the root.}
}
\description{
Requires two multiPhylo objects which contain sequential trees (tree sequences) along a genomic region.
Tips labels in the two tree sequences should correspond (and are assumed to be 1..N) 
Trees within the multiPhylo object should be in order along the genome, and each tree
must have a name which can be converted to a number. The name (number) should give
the (non-inclusive) rightmost genome position covered by that tree.
}
\examples{
genome.trees.dist()
}
