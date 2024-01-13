import { Menu, MenuItem, MenuButton, MenuRadioGroup, SubMenu } from '@szhsin/react-menu';
import '@szhsin/react-menu/dist/core.css';
import '@szhsin/react-menu/dist/index.css';
import '@szhsin/react-menu/dist/theme-dark.css';
import './Toolbar.css';

import IconMenu from "./icons/IconMenu";
import { MediaDevice, Story, Strategy } from './Types'; 

type MainMenuProps = {
    strategies: Strategy[],
    strategy: string | null,
    setStrategy: (strategy: string | null) => void,
    cameras: MediaDevice[],
    camera: string | null,
    setCamera: (camera: string) => void,

    toggleIsPlaying: () => void,
    isPlaying: boolean,
    toggleFullScreen: () => void,
    stories: Story[],
    story_id: string | null,
    setStory: (story_id: string | null) => void,
}

export default function MainMenu(
{
    strategies,
    strategy,
    setStrategy,
    cameras,
    camera,
    setCamera,
    isPlaying,
    toggleIsPlaying,
    toggleFullScreen,
    stories,
    story_id,
    setStory,
}: MainMenuProps) {
    strategies ||= [];
    strategy ||= (strategies.find(strategy => strategy.is_default_for_client) || {slug: null}).slug;
    cameras ||= [];
    strategy ||= null;

    return (
        <Menu menuButton={<MenuButton className="navButton"><IconMenu/></MenuButton>}>
        <SubMenu label="Strategy">
            <MenuRadioGroup
                value={strategy}
                onRadioChange={(e) => setStrategy(e.value)}
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
        <SubMenu label="Story">
            <MenuRadioGroup
                value={story_id}
                onRadioChange={(e) => setStory(e.value)}
            >
                {
                    stories.map(
                        (story, index) => {
                            const image_url = (story.thumbnail_image && story.thumbnail_image.url) ? `/${story.thumbnail_image.url}` : '';

                            return <MenuItem
                                type="radio"
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
        {/*
        <SubMenu label="Camera">
            <MenuRadioGroup
                value={camera}
                onRadioChange={(e) => setCamera(e.value)}
            >
                {
                    cameras.map(
                        (cam, index) => {
                            return <MenuItem
                                type="radio"
                                value={cam.deviceId}
                                key={index}>
                                {cam.label}
                            </MenuItem>
                        }
                    )
                }
            </MenuRadioGroup>
        </SubMenu>
        */}
        </Menu>
    );
}
