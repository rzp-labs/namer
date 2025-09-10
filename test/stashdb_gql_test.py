"""
StashDB GraphQL tests using fake server.
"""

import unittest

from namer.comparison_results import SceneType
from namer.fileinfo import parse_file_name
from namer.metadata_providers.stashdb_provider import StashDBProvider
from namer import metadataapi
from test.utils import environment_stashdb, sample_config


class UnitTestStashDBGQL(unittest.TestCase):
    def test_search_scene_gql(self):
        with environment_stashdb() as (_path, _fake, config):
            name = parse_file_name('Sample Studio - 2022-01-01 - Sample Scene!.mp4', sample_config())
            results = metadataapi.match(name, config)
            self.assertGreaterEqual(len(results.results), 1)
            looked = results.results[0].looked_up
            self.assertEqual(looked.name, 'Sample Scene')
            self.assertEqual(looked.date, '2022-01-01')
            self.assertEqual(looked.site, 'Sample Studio')
            self.assertEqual(looked.parent, 'Sample Network')
            self.assertEqual(looked.type, SceneType.SCENE)
            self.assertIsNotNone(looked.poster_url)

    def test_find_scene_gql(self):
        with environment_stashdb() as (_path, _fake, config):
            provider = StashDBProvider()
            info = provider.get_complete_info(None, 'scenes/s1', config)
            self.assertIsNotNone(info)
            if info:
                self.assertEqual(info.guid, 's1')
                self.assertEqual(info.name, 'Sample Scene')
                self.assertEqual(info.site, 'Sample Studio')
                self.assertEqual(info.parent, 'Sample Network')
                self.assertEqual(info.type, SceneType.SCENE)
                # fingerprints mapped to hashes
                self.assertGreaterEqual(len(info.hashes or []), 1)

    def test_me_user_info_gql(self):
        with environment_stashdb() as (_path, _fake, config):
            user = metadataapi.get_user_info(config)
            self.assertIsNotNone(user)
            if user:
                self.assertEqual(user.get('name'), 'stash-user')


if __name__ == '__main__':
    unittest.main()
