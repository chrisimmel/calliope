port module WebcamApp exposing ( .. )


-- Import Libraries
--------------------------------------------------------------------------------
import Html exposing ( Html )
import Html.Attributes
import Browser
import Task


-- Html App boilerplate
--------------------------------------------------------------------------------
main : Program Int Model Msg
main =
  Browser.element
    { init = init
    , view = view
    , update = update
    , subscriptions = subscriptions
    }

-- Util functions
--------------------------------------------------------------------------------
toCmd : msg -> Cmd msg
toCmd msg =
  let
    onFail    val = val
    onSucceed val = val
  in
    Task.perform msg


-- Model
--------------------------------------------------------------------------------
type alias Model = { width  : Int
                   , height : Int
                   , stream_source : Maybe String
                   }

type alias Flags = { width  : Int
                   , height : Int
                   }

init : Flags -> ( Model, Cmd Msg )
init flags = ( { width  = flags.width
               , height = flags.height
               , stream_source = Nothing
               }
             , initVideoSource { width  = flags.width
                               , height = flags.height
                               }
             )


-- Update
--------------------------------------------------------------------------------
type Msg = UpdateWidth        Int
         | UpdateHeight       Int
         | UpdateStreamSource String
         | InitSuccess        String
         | InitFailure        String


update : Msg -> Model -> ( Model, Cmd Msg )
update msg model =
  case msg of
    UpdateWidth new_width   ->
      ( { model | width = new_width }
      , Cmd.none )
    UpdateHeight new_height ->
      ( { model | height = new_height }
      , Cmd.none )
    UpdateStreamSource new_stream_source ->
      ( { model | stream_source = Just new_stream_source }
      , Cmd.none )
    InitSuccess video_src_url ->
      ( model
      , Cmd.batch [ toCmd ( UpdateStreamSource video_src_url )
                  , playVideoStream { width = model.width
                                    , height = model.height
                                    }
                  ]
      )
    InitFailure error_msg ->
      ( model
      , initVideoSource { width  = model.width
                        , height = model.height
                        }
      )



-- Subscriptions
--------------------------------------------------------------------------------
type alias RequestObject = { width  : Int
                           , height : Int
                           }

port initVideoSource : RequestObject -> Cmd msg
port playVideoStream : RequestObject -> Cmd msg


--------------------------------------------------------------------------------
type alias ResponseSuccessObject = { url : String }

port receiveVideoSource : ( ResponseSuccessObject -> msg ) -> Sub msg

responseSuccessToMsg : ResponseSuccessObject -> Msg
responseSuccessToMsg response = InitSuccess response.url


type alias ResponseFailureObject = { error_msg : String }

port receiveError : ( ResponseFailureObject -> msg ) -> Sub msg

responseFailureToMsg : ResponseFailureObject -> Msg
responseFailureToMsg response = InitFailure response.error_msg


--------------------------------------------------------------------------------
subscriptions : Model -> Sub Msg
subscriptions model =
  Sub.batch [ receiveVideoSource responseSuccessToMsg
            , receiveError       responseFailureToMsg
            ]


-- Video
--------------------------------------------------------------------------------
view : Model -> Html Msg
view model =
  let
    outer_container = Html.div [ Html.Attributes.class "camera" ]
    video_attributes = [ Html.Attributes.id "video"
                       , Html.Attributes.width model.width
                       , Html.Attributes.height model.height
                       ]
    attributes =
      case model.stream_source of
        Just stream_source -> video_attributes ++
                              [ Html.Attributes.src stream_source ]
        Nothing            -> video_attributes
  in
    outer_container [ Html.video attributes [ ] ]
