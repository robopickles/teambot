def add_output_arguments(parser):
    parser.add_argument('--slack-color',
                        required=False,
                        help="Get attachment color. Default is #7CD197",
                        type=str)
    parser.add_argument('--slack-channel',
                        required=False,
                        help='Specify slack channel name',
                        type=str)
