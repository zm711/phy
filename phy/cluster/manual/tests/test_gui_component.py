# -*- coding: utf-8 -*-

"""Test GUI component."""

#------------------------------------------------------------------------------
# Imports
#------------------------------------------------------------------------------

from pytest import yield_fixture
import numpy as np
from numpy.testing import assert_array_equal as ae

from ..gui_component import (ManualClustering,
                             ManualClusteringPlugin,
                             create_cluster_stats,
                             )
from phy.gui import GUI
from phy.io.array import Selector
from phy.utils import Bunch


#------------------------------------------------------------------------------
# Fixtures
#------------------------------------------------------------------------------

@yield_fixture
def manual_clustering(qtbot, gui, cluster_ids, cluster_groups,
                      quality, similarity):
    spike_clusters = np.array(cluster_ids)

    mc = ManualClustering(spike_clusters,
                          cluster_groups=cluster_groups,
                          shortcuts={'undo': 'ctrl+z'},
                          )
    mc.attach(gui)

    mc.add_column(quality, name='quality')
    mc.set_default_sort('quality', 'desc')
    mc.set_similarity_func(similarity)

    yield mc
    del mc


@yield_fixture
def gui(qtbot):
    gui = GUI(position=(200, 100), size=(500, 500))
    gui.show()
    qtbot.waitForWindowShown(gui)
    yield gui
    qtbot.wait(5)
    gui.close()
    del gui
    qtbot.wait(5)


#------------------------------------------------------------------------------
# Test cluster stats
#------------------------------------------------------------------------------

def test_create_cluster_stats(model):
    selector = Selector(spike_clusters=model.spike_clusters,
                        spikes_per_cluster=model.spikes_per_cluster)
    cs = create_cluster_stats(model, selector=selector)
    assert cs.mean_masks(1).shape == (model.n_channels,)
    assert cs.mean_features(1).shape == (model.n_channels,
                                         model.n_features_per_channel)
    assert cs.mean_waveforms(1).shape == (model.n_samples_waveforms,
                                          model.n_channels)
    assert 1 <= cs.best_channels(1).shape[0] <= model.n_channels
    assert 0 < cs.max_waveform_amplitude(1) < 1
    assert cs.mean_masked_features_score(1, 2) > 0


#------------------------------------------------------------------------------
# Test GUI component
#------------------------------------------------------------------------------

def test_manual_clustering_plugin(qtbot, gui):
    model = Bunch(spike_clusters=[0, 1, 2],
                  cluster_groups=None,
                  n_features_per_channel=2,
                  waveforms=np.zeros((3, 4, 1)),
                  features=np.zeros((3, 1, 2)),
                  masks=np.zeros((3, 1)),
                  )
    state = Bunch()
    ManualClusteringPlugin().attach_to_gui(gui, model=model, state=state)


def test_manual_clustering_edge_cases(manual_clustering):
    mc = manual_clustering

    # Empty selection at first.
    ae(mc.clustering.cluster_ids, [0, 1, 2, 10, 11, 20, 30])

    mc.select([0])
    assert mc.selected == [0]

    mc.undo()
    mc.redo()

    # Merge.
    mc.merge()
    assert mc.selected == [0]

    mc.merge([])
    assert mc.selected == [0]

    mc.merge([10])
    assert mc.selected == [0]

    # Split.
    mc.split([])
    assert mc.selected == [0]

    # Move.
    mc.move([], 'ignored')

    mc.save()


def test_manual_clustering_skip(qtbot, gui, manual_clustering):
    mc = manual_clustering

    # yield [0, 1, 2, 10, 11, 20, 30]
    # #      i, g, N,  i,  g,  N, N
    expected = [30, 20, 11, 2, 1]

    for clu in expected:
        mc.cluster_view.next()
        assert mc.selected == [clu]


def test_manual_clustering_merge(manual_clustering):
    mc = manual_clustering

    mc.cluster_view.select([30])
    mc.similarity_view.select([20])
    assert mc.selected == [30, 20]

    mc.merge()
    assert mc.selected == [31, 11]

    mc.undo()
    assert mc.selected == [30, 20]

    mc.redo()
    assert mc.selected == [31, 11]


def test_manual_clustering_split(manual_clustering):
    mc = manual_clustering

    mc.select([1, 2])
    mc.split([1, 2])
    assert mc.selected == [31]

    mc.undo()
    assert mc.selected == [1, 2]

    mc.redo()
    assert mc.selected == [31]


def test_manual_clustering_split_2(gui, quality, similarity):
    spike_clusters = np.array([0, 0, 1])

    mc = ManualClustering(spike_clusters)
    mc.attach(gui)

    mc.add_column(quality, name='quality')
    mc.set_default_sort('quality', 'desc')
    mc.set_similarity_func(similarity)

    mc.split([0])
    assert mc.selected == [2, 3]


def test_manual_clustering_move_1(manual_clustering):
    mc = manual_clustering

    mc.select([20])
    assert mc.selected == [20]

    mc.move([20], 'noise')
    assert mc.selected == [11]

    mc.undo()
    assert mc.selected == [20]

    mc.redo()
    assert mc.selected == [11]


def test_manual_clustering_move_2(manual_clustering):
    mc = manual_clustering

    mc.select([20])
    mc.similarity_view.select([10])

    assert mc.selected == [20, 10]

    mc.move([10], 'noise')
    assert mc.selected == [20, 2]

    mc.undo()
    assert mc.selected == [20, 10]

    mc.redo()
    assert mc.selected == [20, 2]


#------------------------------------------------------------------------------
# Test shortcuts
#------------------------------------------------------------------------------

def test_manual_clustering_action_reset(qtbot, manual_clustering):
    mc = manual_clustering

    mc.actions.select([10, 11])

    mc.actions.reset()
    assert mc.selected == [30]

    mc.actions.next()
    assert mc.selected == [30, 20]

    mc.actions.next()
    assert mc.selected == [30, 11]

    mc.actions.previous()
    assert mc.selected == [30, 20]


def test_manual_clustering_action_nav(qtbot, manual_clustering):
    mc = manual_clustering

    mc.actions.reset()
    assert mc.selected == [30]

    mc.actions.next_best()
    assert mc.selected == [20]

    mc.actions.previous_best()
    assert mc.selected == [30]


def test_manual_clustering_action_move_1(qtbot, manual_clustering):
    mc = manual_clustering

    mc.actions.next()

    assert mc.selected == [30]
    mc.actions.move_best_to_noise()

    assert mc.selected == [20]
    mc.actions.move_best_to_mua()

    assert mc.selected == [11]
    mc.actions.move_best_to_good()

    assert mc.selected == [2]

    mc.cluster_meta.get('group', 30) == 'noise'
    mc.cluster_meta.get('group', 20) == 'mua'
    mc.cluster_meta.get('group', 11) == 'good'

    # qtbot.stop()


def test_manual_clustering_action_move_2(manual_clustering):
    mc = manual_clustering

    mc.select([30])
    mc.similarity_view.select([20])

    assert mc.selected == [30, 20]
    mc.actions.move_similar_to_noise()

    assert mc.selected == [30, 11]
    mc.actions.move_similar_to_mua()

    assert mc.selected == [30, 2]
    mc.actions.move_similar_to_good()

    assert mc.selected == [30, 1]

    mc.cluster_meta.get('group', 20) == 'noise'
    mc.cluster_meta.get('group', 11) == 'mua'
    mc.cluster_meta.get('group', 2) == 'good'


def test_manual_clustering_action_move_3(manual_clustering):
    mc = manual_clustering

    mc.select([30])
    mc.similarity_view.select([20])

    assert mc.selected == [30, 20]
    mc.actions.move_all_to_noise()

    assert mc.selected == [11, 2]
    mc.actions.move_all_to_mua()

    assert mc.selected == [1]
    mc.actions.move_all_to_good()

    assert mc.selected == [1]

    mc.cluster_meta.get('group', 30) == 'noise'
    mc.cluster_meta.get('group', 20) == 'noise'

    mc.cluster_meta.get('group', 11) == 'mua'
    mc.cluster_meta.get('group', 10) == 'mua'

    mc.cluster_meta.get('group', 2) == 'good'
    mc.cluster_meta.get('group', 1) == 'good'
