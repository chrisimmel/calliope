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
}: MainMenuProps) {
    strategies ||= [];
    strategies = strategies.filter((strat) => allowExperimental || !strat.is_experimental);
    strategy ||= (strategies.find(strategy => strategy.is_default_for_client) || {slug: null}).slug;
    strategy ||= null;

    return (
        <Menu menuButton={<MenuButton className="navButton"><IconMenu/></MenuButton>}>
            <SubMenu label="Story">
                <SubMenu label="Pick a story in progress...">
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
                <SubMenu label="Start a new story by...">
                    <MenuRadioGroup
                        value={strategy}
                        onRadioChange={(e) => startNewStory(e.value)}
                    >
                        {
                            strategies.map(
                                (strat, index) => {
                                    return <MenuItem
                                        type="radio"
                                        value={strat.slug}
                                        key={index}>
                                        {strat.slug}
                                    </MenuItem>
                                }
                            )
                        }
                    </MenuRadioGroup>
                </SubMenu>
                <SubMenu label="Send a photo to start a new story by...">
                    <MenuRadioGroup
                        value={strategy}
                        onRadioChange={(e) => startNewStoryWithPhoto(e.value)}
                    >
                        {
                            strategies.map(
                                (strat, index) => {
                                    return <MenuItem
                                        type="radio"
                                        value={strat.slug}
                                        key={index}>
                                        {strat.slug}
                                    </MenuItem>
                                }
                            )
                        }
                    </MenuRadioGroup>
                </SubMenu>
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
