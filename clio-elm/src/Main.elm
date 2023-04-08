module Main exposing (..)

import Browser
import Json.Decode as Decode exposing (Decoder, map2, field, list, string)
import Html exposing (..)
import Html.Attributes exposing (style)
import Html.Events exposing (..)
import Http
import List exposing (head, map)
import Maybe exposing (withDefault)

-- MAIN


main =
  Browser.element
    { init = init
    , update = update
    , subscriptions = subscriptions
    , view = view
    }



-- MODEL

type Model
  = Failure
  | Loading
  | Success (List Frame)


type alias Frame =
  { text : String
  , image_url : Maybe String
  }


init : () -> (Model, Cmd Msg)
init _ =
  (Loading, getFrames)



-- UPDATE


type Msg
  = MorePlease
  | GotFrames (Result Http.Error (List Frame))


update : Msg -> Model -> (Model, Cmd Msg)
update msg model =
  case msg of
    MorePlease ->
      (Loading, getFrames)

    GotFrames result ->
      case result of
        Ok frames ->
          (Success frames, Cmd.none)

        Err _ ->
          (Failure, Cmd.none)



-- SUBSCRIPTIONS


subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.none



-- VIEW


view : Model -> Html Msg
view model =
  div []
    [ h2 [] [ text "Current Frame" ]
    , viewFrame model
    ]


viewFrame : Model -> Html Msg
viewFrame model =
  case model of
    Failure ->
      div []
        [ text "I could not load a frame. "
        , button [ onClick MorePlease ] [ text "Try Again!" ]
        ]

    Loading ->
      text "Loading..."

    Success frames ->
      div []
        [ button [ onClick MorePlease, style "display" "block" ] [ text "More Please!" ]
        , blockquote [] [ text (
            case (head frames) of
                Nothing ->
                    ""

                Just frame ->
                    frame.text
            )
        ]
        ]



-- HTTP


getFrames : Cmd Msg
getFrames =
  Http.get
    { url = """http://localhost:8008/v1/frames/?api_key=xyzzy&client_id=chris&input_text=Mirrors and candles.&output_image_format=image/png&strategy=continuous_v0"""
    , expect = Http.expectJson GotFrames frameListDecoder
    }

frameListDecoder : Decoder (List Frame)
frameListDecoder =
  list frameDecoder

frameDecoder : Decoder Frame
frameDecoder =
  map2 Frame
    (Decode.field "text" string)
    (Decode.maybe (Decode.field "image" imageDecoder))

imageDecoder : Decoder String
imageDecoder =
  Decode.field "url" string

