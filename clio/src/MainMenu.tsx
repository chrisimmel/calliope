import { Menu, MenuItem, MenuButton, MenuRadioGroup, SubMenu } from '@szhsin/react-menu';
import '@szhsin/react-menu/dist/core.css';
import '@szhsin/react-menu/dist/index.css';
import '@szhsin/react-menu/dist/theme-dark.css';
import './Toolbar.css';

import IconMenu from "./icons/IconMenu";
import { MediaDevice, Strategy } from './Types'; 

type MainMenuProps = {
    strategies: Strategy[],
    strategy: string | null,
    setStrategy: (strategy: string | null) => void,
    cameras: MediaDevice[],
    camera: string | null,
    setCamera: (camera: string) => void,
}

export default function MainMenu({strategies, strategy, setStrategy, cameras, camera, setCamera}: MainMenuProps) {
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
        </Menu>
    );
}
