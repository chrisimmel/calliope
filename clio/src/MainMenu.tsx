import { Menu, MenuItem, MenuButton, MenuRadioGroup, SubMenu } from '@szhsin/react-menu';
import '@szhsin/react-menu/dist/core.css';
import '@szhsin/react-menu/dist/index.css';
import '@szhsin/react-menu/dist/theme-dark.css';
import './Toolbar.css';

import IconMenu from "./icons/IconMenu";
import { MediaDevice, Story, Strategy } from './Types'; 

type MainMenuProps = {
    allowExperimental: boolean
    strategies: Strategy[],
    strategy: string | null,
    startNewStory: (strategy: string | null) => void,
    startNewStoryWithPhoto: (strategy: string | null) => void,

    toggleIsPlaying: () => void,
    isPlaying: boolean,
    toggleFullScreen: () => void,
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null) => void,
    jumpToBeginning: () => void,
    jumpToEnd: () => void,
    selectedFrameNumber: number,
    frameCount: number,
}

export default function MainMenu(
{
    allowExperimental,
    strategies,
    strategy,
    startNewStory,
    startNewStoryWithPhoto,
    isPlaying,
    toggleIsPlaying,
    toggleFullScreen,
    stories,
    story_id,
    setStory,
    jumpToBeginning,
    jumpToEnd,
    selectedFrameNumber,
    frameCount,
}: MainMenuProps) {
    strategies ||= [];
    strategies = strategies.filter((strat) => allowExperimental || !strat.is_experimental);
    strategy ||= (strategies.find(strategy => strategy.is_default_for_client) || {slug: null}).slug;
    strategy ||= null;

    return (
        <Menu menuButton={<MenuButton className="navButton"><IconMenu/></MenuButton>}>
            <SubMenu label="Story">
                {
                    stories.length > 1 &&
                    <SubMenu label="Read or rejoin a story">
                        <MenuRadioGroup
                            value={strategy}
                            onRadioChange={(e) => setStory(e.value)}
                        >
                            {
                                stories.map(
                                    (story, index) => {
                                        const image_url = (story.thumbnail_image && story.thumbnail_image.url) ? `/${story.thumbnail_image.url}` : '';

                                        return <MenuItem
                                            type="radio"
                                            className="story"
                                            value={story.story_id}
                                            key={story.story_id}>
                                            {
                                                image_url &&
                                                <img src={image_url} width={48} height={48}/>
                                            }
                                            {story.title}
                                        </MenuItem>
                                    }
                                )
                            }
                        </MenuRadioGroup>
                    </SubMenu>
                }
                <SubMenu label="Start a new story by">
                    {
                        strategies.map(
                            (strat, index) => {
                                return <SubMenu label={strat.slug}>
                                    <MenuItem
                                        onClick={(e) => startNewStoryWithPhoto(strat.slug)}
                                        key={`${strat.slug}-photo`}>
                                        With photo
                                    </MenuItem>
                                    <MenuItem
                                        onClick={(e) => startNewStory(strat.slug)}
                                        key={`${strat.slug}-nophoto`}>
                                        Without
                                    </MenuItem>
                                </SubMenu>
                            }
                        )
                    }
                </SubMenu>
                {
                    (selectedFrameNumber > 1) &&
                    <MenuItem
                        onClick={(e) => jumpToBeginning()}
                    >
                        Jump to beginning
                    </MenuItem>
                }
                {
                    (selectedFrameNumber < frameCount - 2) &&
                    <MenuItem
                        onClick={(e) => jumpToEnd()}
                    >
                        Jump to end
                    </MenuItem>

                }
            </SubMenu>
            <SubMenu label="Advanced">
                <MenuRadioGroup>
                    <MenuItem
                        onClick={(e) => toggleIsPlaying()}
                    >
                        {isPlaying ? "Pause" : "Play Automatically"}
                    </MenuItem>
                    <MenuItem
                        onClick={(e) => toggleFullScreen()}
                    >
                        Full Screen
                    </MenuItem>
                </MenuRadioGroup>
            </SubMenu>
        </Menu>
    );
}
